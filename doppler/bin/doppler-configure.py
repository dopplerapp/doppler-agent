#!/usr/bin/env python

import doppler
from optparse import OptionParser

# Parse command line options
parser = OptionParser(version="%prog " + doppler.__version__)
parser.add_option(
    "-k", "--api-key", 
    dest="api_key",
    help="Specify API key to use for config generation",
)
parser.add_option(
    "-g", "--generate-config", 
    action="store_true",
    dest="generate_config",
    help="Generate doppler config file at /etc/doppler-agent.conf",
)
parser.add_option(
    "-i", "--install-startup-scripts", 
    action="store_true",
    dest="install_startup_scripts",
    help="Install upstart/init.d startup scripts for the agent",
)
parser.add_option(
    "-s", "--start-agent", 
    action="store_true",
    dest="start_agent",
    help="Start the agent",
)
(options, args) = parser.parse_args()

# Check options are valid
if not (options.generate_config or options.install_startup_scripts or options.start_agent):
    parser.print_help()

# Generate config files
if options.generate_config:
    # Check for --api-key command line flag
    if options.api_key:
        print "would generate_config"
        # TODO: Copy the config template, replace the api key in the string
    else:
        print "Can't generate config file without an API key"

# Install startup scripts
if options.install_startup_scripts:
    print "would install startup scripts"
    # TODO: Check if this is an "upstart" machine (look for initctl command in path)
    # TODO: Install the appropriate init scripts

# Start the agent
if options.start_agent:
    print "would start agent"
    # TODO: Start the agent