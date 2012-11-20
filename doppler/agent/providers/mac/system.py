import re
from doppler.agent.providers import Provider, value_for_column, convert_data_unit, get_lines, first_matching_line

class iostat(Provider):
    """
    Basic IO and CPU related statistics sampled over a defined interval
    """

    command = "iostat -C -w 3 -c 2"
    
    metrics = {
        "system.cpu.user": {
            "title": "CPU User",
            "unit": "%"
        },
        "system.cpu.system": {
            "title": "CPU System",
            "unit": "%"
        },
        "system.cpu.idle": {
            "title": "CPU Idle",
            "unit": "%"
        }
    }
    
    interval = 5

    def parser(self, io):
        lines = get_lines(io)

        legend = next(l for l in lines if l.find("us") != -1).split()
        data = lines[-1].split()

        self.metric("system.cpu.user", value_for_column(legend, data, "us"))
        self.metric("system.cpu.system", value_for_column(legend, data, "sy"))
        self.metric("system.cpu.idle", value_for_column(legend, data, "id"))
        
class top(Provider):
    """
    CPU and memory statistics for the system and all running processes
    """

    # TODO:SM We should really use vmstat as that is in bytes and we dont have to worry about MiB/MB
    command = "top -l 1"
    metrics = {
        "system.memory.used": {
            "title": "Used Memory",
            "unit": "MiB"
        },
        "system.memory.free": {
            "title": "Free Memory",
            "unit": "MiB"
        }
    }
    interval = 5

    PHYSMEM_RE = r"^PhysMem"
    MEMORY_VALUE_RE = r"\d+[BKMGT]"

    def parser(self, io):
        memory_line = first_matching_line(io, self.PHYSMEM_RE)
        if memory_line:
            wired, active, inactive, used, free = re.findall(self.MEMORY_VALUE_RE, memory_line)

            self.metric("system.memory.used", convert_data_unit(used, output_unit="MiB"))
            self.metric("system.memory.free", convert_data_unit(free, output_unit="MiB"))

class sysctl(Provider):
    """
    Provides system configuration information, including total ram and cpu
    """

    command = "sysctl -a"
    states = {
        "system.memory.total": {
            "title": "Total Memory",
            "unit": "MiB"
        }
    }
    interval = 120

    MEMSIZE_RE = r"^hw\.memsize:\s*(\d+)$"

    def parser(self, io):
        for l in io:
            match = re.match(self.MEMSIZE_RE, l)
            if match:
                total, = match.groups()
                self.state("system.memory.total", convert_data_unit(total, output_unit="MiB"))
                break