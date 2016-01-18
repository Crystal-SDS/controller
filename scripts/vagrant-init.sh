#!/usr/bin/env bash
if [[ ! -e "pyactive" ]]; then
    git clone https://github.com/cloudspaces/pyactive.git
    cd pyactive/pyactive_project
    sudo -u python setup.py develop
fi
