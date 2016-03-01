import sys
import subprocess
from . import storlet_mgmt_common
from django.conf import settings
#TODO: Define the parameters.
def create_storage_policy(data):
    storlet_mgmt_common.get_hosts_object()
    if len(data) == 6:
        p = subprocess.Popen(['ansible-playbook',
                              '-s',
                              '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                              settings.ANSIBLE_DIR+'/playbook/swift_create_new_storage_policy.yml',
                              '-e', 'policy_id=' + str(data["policy_id"]),
                              '-e', 'name=' + data["name"],
                              '-e', 'partitions=' + str(data["partitions"]),
                              '-e', 'replicas=' + str(data["replicas"]),
                              '-e', 'time=' + data["time"],
                              '-e', "storage_node=" + data["storage_node"]],
                              env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        storlet_mgmt_common.monitor_playbook_execution(p)
    else:
        p = subprocess.Popen(['ansible-playbook',
                              '-s',
                              '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                              settings.ANSIBLE_DIR+'/playbook/swift_create_new_storage_policy.yml',
                              '-e', 'policy_id=' + str(data["policy_id"]),
                              '-e', 'name=' + data["name"],
                              '-e', 'partitions=' + str(data["partitions"]),
                              '-e', 'replicas=' + str(data["replicas"]),
                              '-e', 'time=' + data["time"],
                              '-e', "storage_node=" + data["storage_node"],
                              '-e', "ec_type=" + str(data["ec_type"]),
                              '-e', "ec_num_data_fragments=" + str(data["ec_num_data_fragments"]),
                              '-e', "ec_num_parity_fragments=" + str(data["ec_num_parity_fragments"]),
                              '-e', "ec_object_segment_size=" + str(data["ec_object_segment_size"])],
                              env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        storlet_mgmt_common.monitor_playbook_execution(p)

    p = subprocess.Popen(['ansible-playbook',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/distribute_ring_to_storage_nodes.yml',
                          '-e', 'policy_id=' + data["policy_id"]],
                          env={"ANSIBLE_HOST_KEY_CHECKING" : "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    storlet_mgmt_common.monitor_playbook_execution(p)
