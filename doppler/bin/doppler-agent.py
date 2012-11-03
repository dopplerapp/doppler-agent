#!/usr/bin/env python

import os
import socket
import doppler
import uuid
import platform

from doppler import __version__ as version
from doppler.agent.collector import Collector
from doppler.utils import trim_docstring

# Load useful machine info
api_key = os.getenv("DOPPLER_API_KEY")
hostname = socket.gethostname()
machine_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))
endpoint = os.getenv("DOPPLER_ENDPOINT")

# Create a metrics collector
collector = Collector(api_key, machine_id, hostname, endpoint)

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