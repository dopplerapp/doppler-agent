import inspect
import pkgutil
import subprocess
import time
import threading
import re

DATA_UNIT_REGEX = r"^(\d+(?:\.\d+)?)([bkmgtp])?(?:i)?(?:b)?$"
DATA_UNIT_POWERS = ["b", "k", "m", "g", "t", "p"]

def get_modules_from_package(package):
    for loader, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        yield __import__(name, fromlist="dummy")

def get_providers_from_module(module):
    for name in dir(module):
        obj = getattr(module, name)
        if obj != Provider and inspect.isclass(obj) and issubclass(obj, Provider):
            yield obj

def get_providers_from_packages(packages):
    for package in packages:
        for module in get_modules_from_package(package):
            for provider in get_providers_from_module(module):
                yield provider

def regex_list_index(l, regex):
    for i, key in enumerate(l):
        m = re.match(regex, key)
        if m:
            return (i, m.groups())

def value_for_column(legend, data, key):
    idx = legend.index(key)
    return data[idx]

def value_for_regex_column(legend, data, regex):
    idx, match_groups = regex_list_index(legend, regex)
    return (data[idx], match_groups)

def convert_data_unit(size_string, output_unit="B", input_unit="B", round_down=True):
    match = re.match(DATA_UNIT_REGEX, size_string, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        input_unit = match.group(2) or input_unit
        input_power = DATA_UNIT_POWERS.index(input_unit.lower())
        output_power = DATA_UNIT_POWERS.index(output_unit.lower())
        
        out = float(val) * 1024**(input_power - output_power)
        if round_down:
            out = int(out)
        
        return out

def first_matching_line(iterator, regexp):
    return next(l for l in iterator if re.search(regexp, l))

def get_lines(file):
    return file.read().strip().split("\n")

class Provider(threading.Thread):
    description = None
    provides = None
    command = None
    interval = 5

    def __init__(self, metrics_store, metadata_store):
        threading.Thread.__init__(self)
        
        self.metrics_store = metrics_store
        self.metadata_store = metadata_store

        if self.provides is None:
            raise Exception("Children must override provides")

        if self.command is None and self.file is None:
            raise Exception("Children must override either 'command' or 'file'")

    def parser(self, output):
        raise Exception("Children must override parser method")

    def metric(self, name, value):
        self.metrics_store.collect(name, value)

    def metadata(self, name, value):
        self.metadata_store.collect(name, value)

    def run(self, continuous=True):
        while continuous:
            if self.command:
                try:
                    p = subprocess.Popen(self.command.split(), stdout=subprocess.PIPE)
                    self.parser(p.stdout)
                finally:
                    p.stdout.close()
            elif self.file:
                with open(self.file) as f:
                    self.parser(f)

            time.sleep(self.interval or self.interval)