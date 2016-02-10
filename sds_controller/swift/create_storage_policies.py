import sys
import subprocess
from . import storlet_mgmt_common
from django.conf import settings
#TODO: Define the parameters.
def create_storage_policy(tenant_name, user_name, user_password):
    storlet_mgmt_common.get_hosts_object()
    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/swift_create_new_storage_policies.yml',
                          '-e', 'policy_id=' + policy_id,
                          '-e', 'name=' + name,
                          '-e', 'partitions=' + partitions,
                          '-e', 'replicas='+replicas,
                          '-e', 'time='+time,
                          '-e', "storage_node="+storage_node],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/distibute_ring_to_storage_node.yml'],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
