import re
from doppler.agent.providers import Provider, value_for_column, value_for_regex_column, convert_data_unit, first_matching_line

class meminfo(Provider):
    """
    Detailed memory and swap metrics
    """

    file = "/proc/meminfo"
    provides = ["system.memory.total", "system.memory.free", "system.memory.active", "system.memory.inactive"]
    interval = 10

    MEMINFO_RE = r"^(\w+):\s+([0-9]+)\s*(kB)?"

    def parser(self, io):
        meminfo_metrics = {}
        for line in io:
            match = re.match(self.MEMINFO_RE, line)
            if match:
                metric, value, unit = match.groups()
                meminfo_metrics[metric] = "%s%s" % (value, unit)
        
        self.metadata("system.memory.total", convert_data_unit(meminfo_metrics["MemTotal"], output_unit="M"))
    
        self.metric("system.memory.free", convert_data_unit(meminfo_metrics["MemFree"], output_unit="M"))
        self.metric("system.memory.active", convert_data_unit(meminfo_metrics["Active"], output_unit="M"))
        self.metric("system.memory.inactive", convert_data_unit(meminfo_metrics["Inactive"], output_unit="M"))

class mpstat(Provider):
    """
    CPU related statistics sampled over a defined period
    """
 
    command = "mpstat 1 3"
    provides = ["system.cpu.user", "system.cpu.system", "system.cpu.idle"]
    interval = 5

    LEGEND_RE = r"(%usr|%user)"
    DATA_RE = r"Average"

    def parser(self, io):
        lines = io.readlines()

        legend_line = first_matching_line(lines, self.LEGEND_RE)
        data_line = first_matching_line(lines, self.DATA_RE)

        if legend_line and data_line:
            legend = legend_line.split()[3:]
            data = data_line.split()[2:]
            
            self.metric("system.cpu.user", value_for_column(legend, data, "%usr"))
            self.metric("system.cpu.system", value_for_column(legend, data, "%sys"))
            self.metric("system.cpu.idle", value_for_column(legend, data, "%idle"))

class iostat(Provider):
    """
    Device I/O statistics sampled over a defined period
    """
    
    command = "iostat -d -x 1 3"
    provides = ["system.disk.read_throughput", "system.disk.write_throughput", "system.disk.wait_time", "system.disk.service_time"]
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