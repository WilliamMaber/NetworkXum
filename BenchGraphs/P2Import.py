from datetime import datetime
import os
import importlib

from pystats2md.micro_bench import MicroBench
from pystats2md.helpers import metric2str, bytes2str

from PyWrappedHelpers.Algorithms import export_edges_into_graph
from P0Config import P0Config


class P2Import(object):
    """
        Performs multithreaded bulk import into DB.
        Saves stats.
    """

    def __init__(self):
        self.conf = P0Config.shared()

    def run(self):
        for dataset in self.conf.datasets:
            # Define a baseline, so we know how much time it took
            # to read the data vs actually importing it into DB
            # and building indexes.
            self.benchmark_parsing_speed(dataset)

            for db in self.conf.databases:
                g = self.conf.make_db(database=db, dataset=dataset)
                self.import_graph(g=g, database=db, dataset=dataset)

    def import_graph(self, g, database: dict, dataset: dict):
        if g is None:
            return

        db_name = database['name']
        dataset_name = dataset['name']
        if (g.count_edges() != 0):
            print(f'-- Skipping: {dataset_name} -> {db_name}')
            return

        dataset_path = self.conf.normalize_path(dataset['path'])
        file_size = os.path.getsize(dataset_path)
        print(f'-- Bulk importing: {dataset_name} -> {db_name}')
        print(f'--- started at:', datetime.now().strftime('%H:%M:%S'))
        print(f'--- file size:', bytes2str(file_size))

        def import_one() -> int:
            g.insert_adjacency_list(dataset_path)
            return g.count_edges()

        counter = MicroBench(
            benchmark_name='Sequential Writes: Import CSV',
            func=import_one,
            database=db_name,
            dataset=dataset_name,
            source=self.conf.default_stats_file,
            device_name=self.conf.device_name,
        )
        counter.run_if_missing()

        print(f'--- edges:', metric2str(counter.count_operations))
        print(f'--- edges/second:', metric2str(counter.ops_per_sec()))
        print(f'--- bytes/second:', bytes2str(file_size / counter.time_elapsed))
        print(f'--- finished at:', datetime.now().strftime('%H:%M:%S'))
        self.conf.default_stats_file.dump_to_file()

    def benchmark_parsing_speed(self, dataset: dict):

        class PseudoGraph(object):
            __edge_type__ = dict
            __max_batch_size__ = 1000000

            def __init__(self):
                self.count = 0

            def biggest_edge_id(self) -> int:
                return self.count

            def upsert_edges(self, es) -> int:
                self.count += len(es)
                return len(es)

        g = PseudoGraph()
        p = self.conf.normalize_path(dataset['path'])
        counter = MicroBench(
            benchmark_name='Sequential Writes: Import CSV',
            func=lambda: export_edges_into_graph(p, g),
            database='Parsing in Python',
            dataset=dataset['name'],
            source=self.conf.default_stats_file,
            device_name=self.conf.device_name,
            limit_iterations=1,
            limit_seconds=None,
            limit_operations=None,
        )
        counter.run_if_missing()


if __name__ == "__main__":
    c = P0Config(device_name='MacbookPro')
    try:
        P2Import().run()
    finally:
        c.default_stats_file.dump_to_file()