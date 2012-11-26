import inspect
import pkgutil
import subprocess
import time
import threading
import re

DATA_UNIT_REGEX = r"^(\d+(?:\.\d+)?)([kmgtp]{1}(?:ib|b)?|b)?$"
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

def convert_data_unit(size_string, output_unit="B", input_unit=None, round_down=True):
    if size_string and output_unit and len(output_unit) > 0:
        match = re.match(DATA_UNIT_REGEX, size_string, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if input_unit is None:
                input_unit = match.group(2) or "b"
            if input_unit and len(input_unit) > 0:
                input_power = DATA_UNIT_POWERS.index(input_unit[0].lower())
                output_power = DATA_UNIT_POWERS.index(output_unit[0].lower())
                
                input_base = 1000
                if input_unit.lower().find('i') != -1:
                    input_base = 1024
                
                output_base = 1000
                if output_unit.lower().find('i') != -1:
                    output_base = 1024
                
                out = val * input_base**input_power
                out = out/float(output_base**output_power)
                if round_down:
                    out = int(out)
                
                return out

def first_matching_line(iterator, regexp):
    return next(l for l in iterator if re.search(regexp, l))

def get_lines(file):
    return file.read().strip().split("\n")

class Provider(threading.Thread):
    metrics = None
    events = None
    states = None
    command = None
    file = None
    interval = 5

    def __init__(self, collector, metrics_store, states_store, events_store):
        threading.Thread.__init__(self)
        
        self.metrics_store = metrics_store
        self.states_store = states_store
        self.events_store = events_store
        
        self.collector = collector

        if self.metrics is None and self.events is None and self.states is None:
            raise Exception("Children must override one of metrics, events or states")

    def parser(self, output):
        raise Exception("Children must override parser method")

    def metric(self, name, value):
        self.metrics_store.collect(name, value)

    def state(self, name, value):
        self.states_store.collect(name, value)
    
    def event(self, name):
        self.events_store.register(name)

    def run(self, continuous=True):
        if self.interval is None:
            self.begin()
        else:
            while continuous:
                if self.command:
                    p = None
                    try:
                        p = subprocess.Popen(self.command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        self.parser(p.stdout)
                    finally:
                        if p:
                            p.stdout.close()
                elif self.file:
                    with open(self.file) as f:
                        self.parser(f)
                else:
                    self.fetch_value()

                time.sleep(self.interval)