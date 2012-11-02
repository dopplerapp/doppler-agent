import re
from doppler.agent.providers import Provider, value_for_column, convert_data_unit, get_lines, first_matching_line

class iostat(Provider):
    """
    Basic IO and CPU related statistics sampled over a defined interval
    """

    command = "iostat -C -w 3 -c 2"
    provides = ["cpu:user", "cpu_system", "cpu_idle"]
    interval = 5

    def parser(self, io):
        lines = get_lines(io)

        legend = next(l for l in lines if l.find("us") != -1).split()
        data = lines[-1].split()

        self.metric("cpu:user", value_for_column(legend, data, "us"))
        self.metric("cpu:system", value_for_column(legend, data, "sy"))
        self.metric("cpu:idle", value_for_column(legend, data, "id"))
        
class top(Provider):
    """
    CPU and memory statistics for the system and all running processes
    """

    command = "top -l 1"
    provides = ["memory:used", "memory:free"]
    interval = 5

    PHYSMEM_RE = r"^PhysMem"
    MEMORY_VALUE_RE = r"\d+[BKMGT]"

    def parser(self, io):
        memory_line = first_matching_line(io, self.PHYSMEM_RE)
        if memory_line:
            wired, active, inactive, used, free = re.findall(self.MEMORY_VALUE_RE, memory_line)

            self.metric("memory:used", convert_data_unit(used, output_unit="M"))
            self.metric("memory:free", convert_data_unit(free, output_unit="M"))

class sysctl(Provider):
    """
    Provides system configuration information, including total ram and cpu
    """

    command = "sysctl -a"
    provides = ["memory:total"]    
    interval = 120

    MEMSIZE_RE = r"^hw\.memsize:\s*(\d+)$"

    def parser(self, io):
        for l in io:
            match = re.match(self.MEMSIZE_RE, l)
            if match:
                total, = match.groups()
                self.metadata("memory:total", convert_data_unit(total, output_unit="M"))
                break