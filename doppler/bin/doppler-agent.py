#!/usr/bin/env python

import os
import socket
import doppler
import uuid
import platform

from doppler import __version__ as version
from doppler.agent.collector import Collector
from doppler.utils import trim_docstring

# TODO:JS Check for command-line flags
# TODO:JS Check for config file
# TODO:JS Quit with warning if no config file found (explain about doppler-configure.py)
# TODO:JS Quit with warning if no api key in config file, or api key doesnt match [0-9a-zA-Z]{4,8}
# TODO:JS Load api_key, endpoint, send_interval from config file

# Load useful machine info
api_key = os.getenv("API_KEY")
hostname = socket.gethostname()
machine_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))
endpoint = os.getenv("ENDPOINT")
send_interval = os.getenv("SEND_INTERVAL")

# Create a metrics collector
collector = Collector(api_key, machine_id, hostname, endpoint, send_interval)

# Print startup banner
print "Starting Doppler Monitoring Agent v%s" % version
print
print "API Key: %s" % api_key
print "Machine ID: %s" % machine_id
print "Hostname: %s" % hostname
print
print "Active metrics providers for your platform (%s)" % platform.system()
for p in collector.active_providers():
    print "%s\n    %s\n    Provides: %s" % (p.__name__, trim_docstring(p.__doc__), ", ".join(p.provides))
print

# Start the metrics collector
collector.start()