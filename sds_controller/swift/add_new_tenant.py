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
import subprocess
from . import storlet_mgmt_common
from django.conf import settings
def add_new_tenant(tenant_name, user_name, user_password):
    storlet_mgmt_common.get_hosts_object()
    print 'ansible-playbook ','-s',' -i', settings.ANSIBLE_DIR+"/playbook/swift_cluster_nodes", settings.ANSIBLE_DIR+'/playbook/storlets_add_new_tenant.yml', ' -e', 'tenant_name=' + tenant_name,' -e', 'user_name=' + user_name,' -e', 'user_password=' + user_password,' -e', 'storlets_image_name_suffix=' + 'ubuntu_14.04_jre7_storlets'
    p = subprocess.Popen(['ansible-playbook',
                                '-s',
    				'-i', settings.ANSIBLE_DIR+"/playbook/swift_cluster_nodes",
    				settings.ANSIBLE_DIR+'/playbook/storlets_add_new_tenant.yml',
    				'-e', 'tenant_name=' + tenant_name,
    				'-e', 'user_name=' + user_name,
    				'-e', 'user_password=' + user_password,
    				'-e', 'storlets_image_name_suffix=' + 'ubuntu_14.04_jre7_storlets' ],
                                env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)

# def usage(argv):
#     print argv[0] + " <tenant_name> <user_name> <user_password>"
#
# def main(argv):
#     if len(argv) != 4:
#         usage(argv)
#         return
#
#     tenant_name = argv[1]
#     user_name = argv[2]
#     user_password = argv[3]
#
#
#     add_new_tenant(settings.ANSIBLE_DIR+"/playbook/swift_cluster_nodes",tenant_name, user_name, user_password)
#
# if __name__ == "__main__":
#     main(sys.argv)
