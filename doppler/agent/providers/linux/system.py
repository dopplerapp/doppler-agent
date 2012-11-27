import re
import os
from doppler.agent.providers import Provider, value_for_column, value_for_regex_column, convert_data_unit, first_matching_line

class loadavg(Provider):
    """
    Load Average
    """
    # TODO:SM Should probably use os.getloadavg() instead :-)
    metrics = {
        "system.load.1min": {
            "title": "1 Minute",
            "unit": "Load"
        },
        "system.load.5min": {
            "title": "5 Minutes",
            "unit": "Load"
        },
        "system.load.15min": {
            "title": "15 Minutes",
            "unit": "Load"
        }
    }
    interval = 10
    
    def fetch_value(self):
        load_avg = os.getloadavg()
        self.metric("system.load.1min", load_avg[0])
        self.metric("system.load.5min", load_avg[1])
        self.metric("system.load.15min", load_avg[2])
        

class meminfo(Provider):
    """
    Detailed memory and swap metrics
    """

    file = "/proc/meminfo"
    states = {
        "system.memory.total" : {
            "title": "Total",
            "unit": "MiB"
        }
    }
    metrics = {
        "system.memory.active": {
            "title": "Active",
            "unit": "MiB"
        },
        "system.memory.inactive": {
            "title": "Inactive",
            "unit": "MiB"
        },
        "system.memory.free": {
            "title": "Free",
            "unit": "MiB"
        }
    }
    interval = 10

    MEMINFO_RE = r"^(\w+):\s+([0-9]+)\s*(kB)?"

    def parser(self, io):
        meminfo_metrics = {}
        for line in io:
            match = re.match(self.MEMINFO_RE, line)
            if match:
                metric, value, unit = match.groups()
                meminfo_metrics[metric] = "%s%s" % (value, unit)
        
        self.state("system.memory.total", convert_data_unit(meminfo_metrics["MemTotal"], output_unit="MiB"))
    
        self.metric("system.memory.free", convert_data_unit(meminfo_metrics["MemFree"], output_unit="MiB"))
        self.metric("system.memory.active", convert_data_unit(meminfo_metrics["Active"], output_unit="MiB"))
        self.metric("system.memory.inactive", convert_data_unit(meminfo_metrics["Inactive"], output_unit="MiB"))

class ps(Provider):
    command = "ps aux"
    states = {
        "system.cpu.top_process": {
            "title": "Process with highest CPU usage",
            "hidden": True
        }
    }
    metrics = {
        "system.cpu.top_process_usage": {
            "title": "CPU Usage",
            "unit": "%"
        }
    }
    interval = 10
    
    def parser(self, io):
        highest_cpu = None
        process = None
        for line in io:
            try:
                elements = line.split()
                cpu_usage = float(elements[2])
                if highest_cpu == None or highest_cpu < cpu_usage:
                    highest_cpu = cpu_usage
                    if len(elements) == 11:
                        process = elements[-1]
                    else:
                        process = " ".join(elements[10:-1])
            except ValueError:
                pass
            
        if process:
            self.state("system.cpu.top_process", process)
            self.metric("system.cpu.top_process_usage", highest_cpu)

class mpstat(Provider):
    """
    CPU related statistics sampled over a defined period
    """
 
    command = "mpstat 1 3"
    metrics = {
        "system.cpu.user": {
            "title": "User",
            "unit": "%"
        },
        "system.cpu.used": {
            "title": "Used",
            "unit": "%"
        },
        "system.cpu.system": {
            "title": "System",
            "unit": "%"
        },
        "system.cpu.idle": {
            "title": "Idle",
            "unit": "%"
        },
        "system.cpu.io_wait": {
            "title": "IO Wait",
            "unit": "%"
        }
    }
    interval = 5

    LEGEND_RE = r"(%usr|%user)"
    DATA_RE = r"Average"

    def parser(self, io):
        lines = io.readlines()

        legend_line = first_matching_line(lines, self.LEGEND_RE)
        data_line = first_matching_line(lines, self.DATA_RE)

        if legend_line and data_line:
            if legend_line[1].lower() == "am" or legend_line[1].lower() == "pm":
                legend = legend_line.split()[3:]
            else:
                legend = legend_line.split()[2:]
            data = data_line.split()[2:]
            
            self.metric("system.cpu.user", value_for_column(legend, data, "%usr"))
            self.metric("system.cpu.system", value_for_column(legend, data, "%sys"))
            self.metric("system.cpu.idle", value_for_column(legend, data, "%idle"))
            self.metric("system.cpu.io_wait", value_for_column(legend, data, "%iowait"))
            self.metric("system.cpu.used", "%.2f" % (100.0 - float(value_for_column(legend, data, "%idle"))))

class iostat(Provider):
    """
    Device I/O statistics sampled over a defined period
    """
    
    command = "iostat -d -x 1 3"
    metrics = {
        "system.disk.read_throughput": {
            "title": "Read Throughput",
            "unit": "B/s",
            "multi": True
        },
        "system.disk.write_throughput": {
            "title": "Write Throughput",
            "unit": "B/s",
            "multi": True
        },
        "system.disk.wait_time": {
            "title": "Wait Time",
            "unit": "ms",
            "multi": True
        },
        "system.disk.service_time": {
            "title": "Service Time",
            "unit": "ms",
            "multi": True
        }
    }
    interval = 5

    LEGEND_RE = r"Device:"

    def parser(self, io):
        output = io.read().strip()

        lines = output.split("\n\n")[-1].split("\n")
        legend = first_matching_line(lines, self.LEGEND_RE).split()[1:]
        
        for device_line in lines[1:]:
            columns = device_line.split()
            device = columns[0]
            data = columns[1:]

            read_throughput, (read_unit,) = value_for_regex_column(legend, data, r"r([kM])B\/s")
            write_throughput, (write_unit,) = value_for_regex_column(legend, data, r"w([kM])B\/s")

            self.metric("system.disk.read_throughput:%s" % device, convert_data_unit(read_throughput, input_unit=read_unit))
            self.metric("system.disk.write_throughput:%s" % device, convert_data_unit(write_throughput, input_unit=write_unit))
            self.metric("system.disk.wait_time:%s" % device, value_for_column(legend, data, "await"))
            self.metric("system.disk.service_time:%s" % device, value_for_column(legend, data, "svctm"))