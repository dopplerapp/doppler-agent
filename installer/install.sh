#!/usr/bin/env bash

#
# Doppler Agent Installer
# http://doppler.io
#
# The source for this installer can be found here:
# https://github.com/dopplerapp/doppler-installer
#
# If you'd like to contribute, we'll happily accept pull requests
#
# If you find any bugs, create an issue here:
# https://github.com/dopplerapp/doppler-installer/issues
#

# Installer configuration
VERSION="0.1.0"
API_KEY=${API_KEY:-"YOUR-API-KEY-HERE"}
PROGRESS_SERVER=${PROGRESS_SERVER:-"http://get.doppler.io"}
PROGRESS_URL="$PROGRESS_SERVER/$API_KEY"

# Check if a file exists
file_exists() {
  [ -f "$1" ]
}

# Check if a command exists
command_exists() {
  type "$1" &> /dev/null ;
}

# Check if a string matches a regex
matches_regex() {
  if command_exists egrep ; then
    echo $1 | egrep -q $2
  fi
}

# Notify our server about installer progress
notify_server() {
  if command_exists curl ; then
    message_type=$1
    shift

    extra_params=""
    for var in "$@" ; do
      extra_params+=" --data-urlencode \"$var\""
    done

    eval "curl -s -d \"hostname=$HOSTNAME&type=$message_type\" $extra_params $PROGRESS_URL" >> /dev/null
  fi
}

# Send installer progress to our servers and print it
track_progress() {
  notify_server "progress" "action=$1"

  printf "\e[32m%s\e[0m %s\n" "***" "$2"
}

# Send installer error to our servers and print it
track_error() {
  notify_server "error" "message=$1"

  printf "\e[31m%s\e[0m %s\n\n" "!!!" "$1"
  printf "\e[31m%s\n%s\e[0m\n" "The Doppler installer failed!" \
  "Check out http://doppler.io/docs or email us at support@doppler.io for help."

  exit 1``
}

# Install packages using the package manager on this machine
install_packages() {
  if [ "$DISTRO" == 'debian' ]; then
    if ! dpkg-query -s $1 >> /dev/null ; then
      sudo apt-get -y install $1
    fi
  elif [ "$DISTRO" == 'rpm' ]; then
    if ! rpm --quiet -q $1 ; then
      sudo yum -t -y install $1
    fi
  fi
}

# Start your engines...
printf "\e[1m#\n# %s\n# \e[0m\n\n" "Doppler monitoring agent installer v$VERSION"
printf "This script downloads the Doppler agent and any dependencies\n"
printf "and starts the monitoring agent on your machine.\n\n"
track_progress "starting-installer" "Starting the Doppler installer"

# Check if the api key looks valid
if ! matches_regex $API_KEY "^[0-9A-Za-z]{4,8}$"; then
  track_error "Your API key ($API_KEY) does not look valid"
fi

# Work out which operating system this machine has
OS=$(uname -s)
if [ "$OS" == "Linux" ] ; then
  true
elif [ "$OS" == "Darwin" ] ; then
  track_error "The Doppler agent doesnt currently support OSX"
else
  track_error "The Doppler agent doesnt currently support Windows"
fi

# Work out which package manager (if any) this machine uses
DISTRO=
if file_exists /etc/debian_version ; then
  DISTRO='debian'
elif file_exists /etc/redhat-release ; then
  DISTRO='rpm'
elif file_exists /etc/system-release ; then
  DISTRO='rpm'
else
  track_error "Your linux distro is not currently supported by this installer"
fi

# Check and download dependencies
track_progress "downloading-dependencies" "Checking and downloading dependencies"
install_packages "python python-setuptools sysstat"

# Download Doppler agent
track_progress "downloading-agent" "Downloading latest Doppler agent"
if command_exists easy_install ; then
  sudo easy_install doppler-agent

  if [ $? -ne 0 ] ; then
    track_error "Could not install the Doppler python gem (easy_install failed)"
  fi
else
  track_error "Could not install the Doppler python gem (easy_install missing)"
fi

# Run initial agent configuration
track_progress "configuring-agent" "Running initial agent configuration"
if command_exists doppler-configure.py ; then
  sudo doppler-configure.py --api-key $API_KEY --generate-config
  if [ $? -ne 0 ] ; then
    track_error "Couldn't configure the agent (doppler-configure failed)"
  fi

  sudo doppler-configure.py --install-startup-scripts
  if [ $? -ne 0 ] ; then
    track_error "Couldn't install startup scripts (doppler-configure failed)"
  fi
else
  track_error "Couldn't configure the agent (doppler-configure missing)"
fi

# Start Doppler agent
track_progress "starting-agent" "Starting Doppler agent"
sudo doppler-configure.py --start-agent
if [ $? -ne 0 ] ; then
  track_error "Couldn't start the agent (doppler-configure failed)"
fi

# Check agent is running ok
pgrep doppler-agent.py || track_error "Couldn't start the agent"

# Notify the server that the installer is finished
notify_server "complete"
printf "\n\n\e[32m%s\n%s\e[0m" \
  "The Doppler monitoring agent is installed and running." \
  "Check http://doppler.io to view your dashboard."