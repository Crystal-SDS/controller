#!/usr/bin/python

'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

'''
@author: eranr
'''

import sys
import select
import subprocess
from swiftclient import client as c
from django.conf import settings
def get_hosts_object():
    os_options = {'tenant_name': settings.MANAGMENT_ACCOUNT}
    url, token = c.get_auth(settings.KEYSTONE_ADMIN_URL, settings.MANAGMENT_ACCOUNT + ":" + settings.MANAGMENT_ADMIN_USERNAME,
                            settings.MANAGMENT_ADMIN_PASSWORD, os_options = os_options,
                            auth_version="2.0")

    response = dict()
    headers, content = c.get_object(
                            url,
                            token,
                            'swift_cluster',
                            'swift_cluster_nodes',
        	            None,
                            None,
                            None,
                            response_dict = response,
                            headers = None)
                            
    assert(response.get('status') == 200)
    f = open(settings.ANSIBLE_DIR+"/playbook/swift_cluster_nodes", "w" )
    f.write(content)
    f.close()

def monitor_playbook_execution(p):
    #stdout = []
    #stderr = []
    stdout_pipe = p.stdout
    stderr_pipe = p.stderr

    while True:
        reads = [stdout_pipe.fileno(), stderr_pipe.fileno()]
        ret = select.select(reads, [], [])

        for fd in ret[0]:
            if fd == stdout_pipe.fileno():
                read = stdout_pipe.readline()
                sys.stdout.write(read)
                #stdout.append(read)
                if "FATAL" in read:
                    raise Exception("Error while executing ansible script")
            if fd == stderr_pipe.fileno():
                read = stderr_pipe.readline()
                sys.stderr.write(read)
                #stderr.append(read)
                if "FATAL" in read:
                    raise Exception("Error while executing ansible script")

        if p.poll() != None:
            break
