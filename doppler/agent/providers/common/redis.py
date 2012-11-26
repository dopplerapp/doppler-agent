import distutils.spawn
import re
import subprocess
from doppler.agent.providers import Provider, value_for_column, value_for_regex_column, convert_data_unit, first_matching_line

class redisInfo(Provider):
    """
    CPU related statistics sampled over a defined period
    """
 
    states = {
        "system.packages.version.redis": {
            "title": "Redis Version"
        }
    }
    metrics = {
        "service.redis.used_memory": {
            "title": "Used Memory",
            "unit": "KiB"
        }
    }
    interval = 10

    def fetch_value(self):
        if distutils.spawn.find_executable("redis-cli"):
            p = subprocess.Popen(("redis-cli", "info"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in p.stdout:
                if line.startswith("redis_version:"):
                    version = line.split(':')[1]
                    self.state("system.packages.version.redis", version.strip())
                elif line.startswith("used_memory:"):
                    used_memory = line.split(':')[1]
                    self.metric("service.redis.used_memory", convert_data_unit(used_memory.strip(), output_unit="KiB"))
        else:
            self.state("system.packages.version.redis", None)