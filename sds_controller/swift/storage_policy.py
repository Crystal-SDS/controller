from django.conf import settings
import subprocess
import select
import sys


# TODO: Define the parameters.
def create(data):
    # get_hosts_object()
    
    print 'lendata', len(data)
    print 'data', data
    
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
                              env={"ANSIBLE_HOST_KEY_CHECKING": "False"},
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        _monitor_playbook_execution(p)
        
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
                              env={"ANSIBLE_HOST_KEY_CHECKING": "False"},
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        _monitor_playbook_execution(p)

    p = subprocess.Popen(['ansible-playbook', '-vvv',
                          '-s',
                          '-i', settings.ANSIBLE_DIR+'/playbook/swift_cluster_nodes',
                          settings.ANSIBLE_DIR+'/playbook/distribute_ring_to_storage_nodes.yml',
                          '-e', 'policy_id=' + data["policy_id"]],
                          env={"ANSIBLE_HOST_KEY_CHECKING": "False"},
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    _monitor_playbook_execution(p)


def _monitor_playbook_execution(p):
    # stdout = []
    # stderr = []
    stdout_pipe = p.stdout
    stderr_pipe = p.stderr

    while True:
        reads = [stdout_pipe.fileno(), stderr_pipe.fileno()]
        ret = select.select(reads, [], [])

        for fd in ret[0]:
            if fd == stdout_pipe.fileno():
                read = stdout_pipe.readline()
                sys.stdout.write(read)
                # stdout.append(read)
                if "FATAL" in read:
                    raise Exception("Error while executing ansible script")
            if fd == stderr_pipe.fileno():
                read = stderr_pipe.readline()
                sys.stderr.write(read)
                # stderr.append(read)
                if "FATAL" in read:
                    raise Exception("Error while executing ansible script")

        if p.poll() != None:
            break
