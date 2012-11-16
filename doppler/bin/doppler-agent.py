#!/usr/bin/env python

import os
import socket
import doppler
import uuid
import platform
import ConfigParser
import sys
import bugsnag
import urllib

from optparse import OptionParser

from doppler import __version__ as version
from doppler.agent.collector import Collector
from doppler.utils import trim_docstring


def exit_with_error(error):
  print error
  sys.exit(1)

# Configure bugsnag
bugsnag.configure(
    api_key = "9423ae3edbd1922973cd0dcc72109f44",
    ignore_classes=["KeyboardInterrupt"]
)

# Parse command line options
parser = OptionParser()
parser.add_option(
    "-c", "--config-file",
    dest="config_filename",
    default="/etc/doppler-agent.conf",
    help="the location of the doppler-agent.conf file",
    metavar="FILE"
)
parser.add_option(
    "-a", "--api-key",
    dest="api_key",
    help="the api key used to identify your account"
)
parser.add_option(
    "-e", "--endpoint",
    dest="endpoint",
    help="the endpoint used to contact doppler"
)
parser.add_option(
    "-s", "--send-interval",
    dest="send_interval",
    type="int",
    help="how often metrics are sent to doppler"
)
(options, args) = parser.parse_args()

# Pull out command line arg values
config_filename = options.config_filename
api_key = options.api_key
endpoint = options.endpoint
send_interval = options.send_interval

# Load the config file
config = ConfigParser.RawConfigParser()
config.read(config_filename)

if api_key is None:
  try:
    api_key = config.get("doppler-agent", "api_key")
  except ConfigParser.NoSectionError:
    exit_with_error("Please ensure the [doppler-agent] section is in " + config_filename)
  except ConfigParser.Error:
    exit_with_error("Please ensure that the api key is either within " + config_filename + " or passed as a parameter to doppler-agent")

if endpoint is None:
  try:
    endpoint = config.get("doppler-agent", "endpoint")
  except ConfigParser.Error:
    # Do nothing here, we revert to default
    pass

if send_interval is None:
  try:
    send_interval = config.getint("doppler-agent", "send_interval")
  except ConfigParser.Error:
    # Do nothing here, we revert to default
    pass

# Check the ApiKey format
if api_key is None or (len(api_key) < 3 and len(api_key) > 9):
  exit_with_error("The Api Key configured is not correct. Please check your Api Key.")

# Verify with Doppler that the ApiKey looks good
try:
  response = urllib.urlopen("http://get.doppler.io/" + api_key + "/check")
  if response.getcode() != 200:
    exit_with_error("The Api Key configured is not correct. Please check your Api Key.")
except IOError: 
  # Do nothing here, we just let it pass, as it would be unreasonable to stop the agent for this
  pass
  
# Load useful machine info
hostname = socket.gethostname()
machine_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))

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