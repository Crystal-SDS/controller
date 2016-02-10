import sys
import subprocess
from . import storlet_mgmt_common
from django.conf import settings
#TODO: Define the parameters.
def create_storage_policy(data):
    storlet_mgmt_common.get_hosts_object()
    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/swift_create_new_storage_policy.yml',
                          '-e', 'policy_id=' + data["policy_id"],
                          '-e', 'name=' + data["name"],
                          '-e', 'partitions=' + data["partitions"],
                          '-e', 'replicas=' + str(data["replicas"]),
                          '-e', 'time=' + data["time"],
                          '-e', "storage_node=" + data["storage_node"]],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/distibute_ring_to_storage_nodes.yml'],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
