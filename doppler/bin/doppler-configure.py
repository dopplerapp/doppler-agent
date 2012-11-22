#!/usr/bin/env python

import os
import shutil
import sys
import subprocess
from string import Template
from optparse import OptionParser

import doppler

CONFIG_TEMPLATES_PATH = os.path.join(os.path.dirname(doppler.__file__), "config")

DEFAULT_CONFIG_PATH  = "/etc/doppler-agent.conf"
DEFAULT_UPSTART_PATH = "/etc/init/doppler-agent.conf"

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

def run_silently(command):
    worked = True
    with open(os.devnull, "w") as devnull:
        try:
            subprocess.check_call(command.split(), stdout=devnull, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            worked = False
    return worked

def can_write_file(path):
    has_write_permission = False
    if os.path.isfile(path):
        if os.access(path, os.W_OK):
            has_write_permission = True
    else:
        if os.access(os.path.dirname(path), os.W_OK):
            has_write_permission = True
    
    return has_write_permission

def machine_uses_upstart():
    return os.path.isfile("/sbin/initctl")

# Check options are valid
if not (options.generate_config or options.install_startup_scripts or options.start_agent):
    parser.print_help()

# Generate config files
if options.generate_config:
    # TODO: Don't overwrite existing config files!!!

    # Check for --api-key command line flag
    if options.api_key:
        if can_write_file(DEFAULT_CONFIG_PATH):
            # Generate the config file from the template
            config = None
            with open(os.path.join(CONFIG_TEMPLATES_PATH, "doppler-agent.conf")) as f:            
                config_template = f.read()
                config = Template(config_template).substitute(api_key=options.api_key)

            # Write the new config file
            with open(DEFAULT_CONFIG_PATH, "w") as f:
                f.write(config)
        else:
            sys.exit("Error! We don't have permission to write to %s, try running as sudo." % DEFAULT_CONFIG_PATH)

    else:
        sys.exit("Can't generate config file without an API key")

# Install startup scripts
if options.install_startup_scripts:
    # Check which init system this machine uses
    if machine_uses_upstart():
        if can_write_file(DEFAULT_UPSTART_PATH):
            shutil.copyfile(os.path.join(CONFIG_TEMPLATES_PATH, "doppler-agent.upstart"), DEFAULT_UPSTART_PATH)
        else:
            sys.exit("Error! We don't have permission to write to %s, try running as sudo." % DEFAULT_UPSTART_PATH)
    else:
        sys.exit("Error! We currently only support starting the agent with upstart")

# Start the agent
if options.start_agent:
    if machine_uses_upstart():
        if os.path.isfile(DEFAULT_UPSTART_PATH):
            worked = run_silently("initctl start doppler-agent") or run_silently("initctl restart doppler-agent")
            if not worked:
                sys.exit("Got bad return code from upstart, process probably didn't start")
        else:
            sys.exit("Error! Couldn't find doppler-agent upstart script, try running with --generate-startup-scripts")
    else:
        sys.exit("Error! We currently only support starting the agent with upstart")