#!/usr/bin/env bash
if [[ ! -e "pyactive" ]]; then
    git clone https://github.com/cloudspaces/pyactive.git
    cd pyactive/pyactive_project
    sudo python setup.py develop
fi

# fix hiera config file (Warning: Config file /etc/puppet/hiera.yaml not found, using Hiera defaults)
if [ ! -e /etc/puppet/hiera.yaml ]
then
	# Default Config Values
	# If the config file exists but has no data, the default settings will be equivalent to the following:
	#	---
	#	:backends: yaml
	#	:yaml:
	#  		:datadir: /var/lib/hiera
	#	:hierarchy: common
	#	:logger: console
	su -c "touch /etc/puppet/hiera.yaml" 
fi

# fix tty error (stdin: is not a tty)
sudo sed -i 's/^mesg n$/tty -s \&\& mesg n/g' /root/.profile
