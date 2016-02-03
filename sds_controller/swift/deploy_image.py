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
@author: cdoron
'''

import sys
import select
import subprocess
from . import storlet_mgmt_common
from django.conf import settings

def deploy_image(tenant_name, tar_object_name, tenant_image_name):
    storlet_mgmt_common.get_hosts_object()

    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', '/opt/ibm/ansible/playbook/swift_cluster_nodes',
                          '/opt/ibm/ansible/playbook/push_tenant_image.yml',
                          '-e', 'tar_object_name=' + tar_object_name,
                          '-e', 'tenant_name=' + tenant_name,
                          '-e', 'tenant_image_name=' + tenant_image_name],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', '/opt/ibm/ansible/playbook/swift_cluster_nodes',
                          '/opt/ibm/ansible/playbook/pull_tenant_image.yml',
                          '-e', 'tenant_name=' + tenant_name],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)

# def usage(argv):
#     print argv[0] + " <tenant_name> <tar_object_name> <tenant_image_name>"
#
# def main(argv):
#     if len(argv) != 4:
#         usage(argv)
#         return
#
#     tenant_name = argv[1]
#     tar_object_name = argv[2]
#
#     tenant_image_name = argv[3]
#
#     deploy_image(tenant_name, tar_object_name, tenant_image_name)
#
# if __name__ == "__main__":
#     main(sys.argv)
