import json
from typing import Optional
from os import path
import platform

from helpers.shared import StatsCounter


class StatsFile(object):

    def __init__(self, filename='bench/stats.json'):
        self.filename = filename
        self.device_name = platform.node()
        self.results = []
        self.reset_from_file(self.filename)

    # def __del__(self):
    #     self.dump_to_file(self.filename)

    def bench_matches(
        self,
        bench: object,
        wrapper_name: str,
        operation_name: str,
    ) -> bool:
        if bench['device'] != self.device_name:
            return False
        if bench['wrapper_name'] != wrapper_name:
            return False
        if bench['operation_name'] != operation_name:
            return False
        return True

    def find(
        self,
        wrapper_class: type,
        operation_name: str,
    ) -> Optional[StatsCounter]:
        def predicate(b):
            wrapper_name = str(wrapper_class)
            return self.bench_matches(b, wrapper_name, operation_name)
        return next(filter(predicate, self.results), None)

    def insert(
        self,
        wrapper_class: type,
        operation_name: str,
        stats: StatsCounter,
    ):
        bench = self.find(wrapper_class, operation_name)
        stats_serialized = {
            'device': self.device_name,
            'time_elapsed': stats.time_elapsed,
            'count_operations': stats.count_operations,
            'msecs_per_operation': stats.msecs_per_op(),
            'operations_per_second': stats.ops_per_sec(),
            'operation_name': operation_name,
            'wrapper_name': str(wrapper_class),
        }
        if bench is None:
            self.results.append(stats_serialized)
        else:
            bench = stats_serialized

    def reset_from_file(self, filename=None):
        if filename is None:
            filename = self.filename
        if not path.exists(filename):
            self.results = []
            return
        self.results = json.load(open(filename, 'r'))

    def dump_to_file(self, filename=None):
        if filename is None:
            filename = self.filename
        json.dump(self.results, open(filename, 'w'), indent=4)
