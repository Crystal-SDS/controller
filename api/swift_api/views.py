from paramiko.ssh_exception import SSHException, AuthenticationException
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from shutil import copyfile
from swiftclient import client as swift_client
from swift.common.ring import RingBuilder
from swift.common import exceptions
from operator import itemgetter
import ConfigParser
import os
import glob
import json
import math
import logging
import requests
import paramiko
from socket import inet_aton
from api.common import JSONResponse, get_redis_connection, to_json_bools, get_token_connection
from api.exceptions import FileSynchronizationException


logger = logging.getLogger(__name__)


#
# Storage Policies
#

def update_sp_files(path, policy_id, d):
    storage_policy_key = 'storage-policy:' + policy_id

    swift_file = os.path.join(path, 'swift.conf')

    configParser = ConfigParser.RawConfigParser()
    configParser.read(swift_file)

    if not configParser.has_section(storage_policy_key):
        configParser.add_section(storage_policy_key)

    for key, value in d.iteritems():
        configParser.set(storage_policy_key, key, value)

    with open(swift_file, 'wb') as configfile:
        configParser.write(configfile)


def get_policy_file_path(dir_path, policy_id):
    object_builder_key = 'object.builder' if policy_id == '0' else 'object-' + policy_id + '.builder'
    return os.path.join(dir_path, object_builder_key)


def get_swift_cfg_path(dir_path):
    return os.path.join(dir_path, 'swift.conf')


@csrf_exempt
def storage_policies(request):
    """
    Creates a storage policy to swift with an specific ring.
    Allows create replication storage policies and erasure code storage policies
    """

    if request.method == "GET":
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        keys = r.keys("storage-policy:*")
        storage_policy_list = []
        for key in keys:
            storage_policy = r.hgetall(key)
            to_json_bools(storage_policy, 'deprecated', 'default', 'deployed')
            storage_policy['id'] = str(key).split(':')[-1]
            storage_policy['devices'] = json.loads(storage_policy['devices'])
            storage_policy_list.append(storage_policy)
        return JSONResponse(storage_policy_list, status=status.HTTP_200_OK)

    if request.method == "POST":
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = JSONParser().parse(request)

        try:
            sp_id = str(r.incr('storage-policies:id'))
            key = 'storage-policy:' + sp_id

            ring = RingBuilder(int(data['partition_power']), int(data['replicas']), int(data['time']))
            ring.save(get_policy_file_path(settings.SWIFT_CFG_TMP_DIR, sp_id))

            r.hmset(key, data)
        except:
            return JSONResponse('Error creating the Storage Policy', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse('Account created successfully', status=status.HTTP_201_CREATED)

    return JSONResponse('Only HTTP POST requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storage_policy_detail(request, storage_policy_id):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "storage-policy:" + storage_policy_id
    if request.method == 'GET':
        if r.exists(key):
            storage_policy = r.hgetall(key)
            to_json_bools(storage_policy, 'deprecated', 'default', 'deployed')
            storage_policy['storage_policy_id'] = storage_policy_id
            storage_policy['devices'] = json.loads(storage_policy['devices'])
            devices = []
            for device in storage_policy['devices']:
                object_node_id, device_id = device[0].split(':')
                object_node = r.hgetall('object_node:' + object_node_id)
                object_node_devices = json.loads(object_node['devices'])
                device_detail = object_node_devices[device_id]
                device_detail['id'] = device[0]
                device_detail['region'] = r.hgetall('region:' + object_node['region_id'])['name']
                device_detail['zone'] = r.hgetall('zone:' + object_node['zone_id'])['name']
                devices.append(device_detail)
            storage_policy['devices'] = devices
            return JSONResponse(storage_policy, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if r.exists(key):
            data = JSONParser().parse(request)
            try:
                data['deployed'] = False
                r.hmset(key, data)
                return JSONResponse("Storage Policy updated", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error updating storage policy", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        if r.exists(key):
            try:
                policy_file_path = get_policy_file_path(settings.SWIFT_CFG_DEPLOY_DIR, storage_policy_id)
                if os.path.isfile(policy_file_path):
                    os.remove(policy_file_path)
                os.remove(get_policy_file_path(settings.SWIFT_CFG_TMP_DIR, storage_policy_id))

                deploy_swift_file = get_swift_cfg_path(settings.SWIFT_CFG_DEPLOY_DIR)

                configParser = ConfigParser.RawConfigParser()
                configParser.read(deploy_swift_file)

                configParser.remove_section(key)

                with open(deploy_swift_file, 'wb') as configfile:
                    configParser.write(configfile)

                r.delete(key)

                if not r.keys('storage-policy:*'):
                    r.delete('storage-policies:id')

                return JSONResponse("Storage Policy deleted", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error deleting storage policy", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storage_policy_disks(request, storage_policy_id):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "storage-policy:" + storage_policy_id

    if request.method == 'GET':
        if r.exists(key):
            storage_policy = r.hgetall(key)
            storage_policy['devices'] = json.loads(storage_policy['devices'])
            all_devices = []
            for node_key in r.keys('object_node:*'):
                node = r.hgetall(node_key)
                all_devices += [node_key.split(':')[1] + ':' + device for device in json.loads(node['devices']).keys()]

            current_devices = [dev[0] for dev in storage_policy['devices']]
            available_devices = [device for device in all_devices if device not in current_devices]
            available_devices_detail = []
            for device in available_devices:
                object_node_id, device_id = device.split(':')
                object_node = r.hgetall('object_node:' + object_node_id)
                device_detail = json.loads(object_node['devices'])[device_id]
                device_detail['id'] = device
                device_detail['region'] = r.hgetall('region:' + object_node['region_id'])['name']
                device_detail['zone'] = r.hgetall('zone:' + object_node['zone_id'])['name']
                available_devices_detail.append(device_detail)
            return JSONResponse(available_devices_detail, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if r.exists(key):
            disk = JSONParser().parse(request)

            object_node_id, device_id = disk.split(':')
            object_node = r.hgetall('object_node:' + object_node_id)
            device_detail = json.loads(object_node['devices'])[device_id]
            region = r.hgetall('region:' + object_node['region_id'])['name']
            zone = r.hgetall('zone:' + object_node['zone_id'])['name']

            tmp_policy_file = get_policy_file_path(settings.SWIFT_CFG_TMP_DIR, storage_policy_id)

            ring = RingBuilder.load(tmp_policy_file)
            ring_dev_id = ring.add_dev({'weight': 100, 'region': region, 'zone': zone, 'ip': object_node['ip'], 'port': '6000', 'device': device_id})
            ring.save(tmp_policy_file)

            storage_policy = r.hgetall(key)
            storage_policy['devices'] = json.loads(storage_policy['devices'])
            storage_policy['devices'].append((disk, ring_dev_id))
            storage_policy['devices'] = json.dumps(storage_policy['devices'])
            r.hset(key, 'devices', storage_policy['devices'])
            r.hset(key, 'deployed', False)

            return JSONResponse('Disk added correctly', status=status.HTTP_200_OK)
        else:
            return JSONResponse('Disk could not be added.', status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def delete_storage_policy_disks(request, storage_policy_id, disk_id):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "storage-policy:" + storage_policy_id

    if request.method == 'DELETE':
        if r.exists(key):
            try:

                tmp_policy_file = get_policy_file_path(settings.SWIFT_CFG_TMP_DIR, storage_policy_id)

                found = False
                storage_policy = r.hgetall(key)
                storage_policy['devices'] = json.loads(storage_policy['devices'])

                for i, disk in enumerate(storage_policy['devices']):
                    if disk_id == disk[0]:
                        found = True
                        ring = RingBuilder.load(tmp_policy_file)
                        ring.remove_dev(disk[1])
                        ring.save(tmp_policy_file)
                        del storage_policy['devices'][i]
                        storage_policy['devices'] = json.dumps(storage_policy['devices'])
                        r.hset(key, 'devices', storage_policy['devices'])
                        r.hset(key, 'deployed', False)

                        return JSONResponse("Disk removed", status=status.HTTP_204_NO_CONTENT)

                if not found:
                    return JSONResponse('Disk not found', status=status.HTTP_404_NOT_FOUND)

            except RedisError:
                return JSONResponse("Error updating storage policy", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def deploy_storage_policy(request, storage_policy_id):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "storage-policy:" + storage_policy_id

    if request.method == "POST":
        if r.exists(key):
            try:
                tmp_policy_file = get_policy_file_path(settings.SWIFT_CFG_TMP_DIR, storage_policy_id)
                deploy_policy_file = get_policy_file_path(settings.SWIFT_CFG_DEPLOY_DIR, storage_policy_id)

                ring = RingBuilder.load(tmp_policy_file)
                ring.rebalance()
                ring.save(tmp_policy_file)

                data = r.hgetall(key)
                update_sp_files(settings.SWIFT_CFG_DEPLOY_DIR, storage_policy_id, {'name': data['name'], 'deprecated': data['deprecated'],
                                                                                   'default': data['default'], 'deployed': 'True'})

                copyfile(tmp_policy_file, deploy_policy_file)

                r.hset(key, 'deployed', 'True')

                return JSONResponse('Storage policy deployed correctly', status=status.HTTP_200_OK)
            except RedisError:
                return JSONResponse('Storage policy could not be deployed', status=status.HTTP_400_BAD_REQUEST)
            except exceptions.RingBuilderError, e:
                return JSONResponse('Storage policy could not be deployed. Error message: %s' % e.message, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Only HTTP POST requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def load_swift_policies(request):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == "POST":

        # 1st step: Copy de swift.conf file from a Proxy Server to a local Crystal directory
        proxy_nodes = r.keys("proxy_node:*")
        if proxy_nodes:
            node = r.hgetall(proxy_nodes[0])
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(node['ip'], username=node['ssh_username'], password=node['ssh_password'])

            try:
                sftp_client = ssh_client.open_sftp()
                swift_etc_path = '/etc/swift/'
                remote_swift_file = swift_etc_path+'swift.conf'
                local_swift_file_deploy = get_swift_cfg_path(settings.SWIFT_CFG_DEPLOY_DIR)
                sftp_client.get(remote_swift_file, local_swift_file_deploy)

                remote_file_list = sftp_client.listdir(swift_etc_path)
                for r_file in remote_file_list:
                    if r_file.startswith('object') and r_file.endswith('.builder'):
                        remote_file = swift_etc_path+r_file
                        local_file_tmp = os.path.join(settings.SWIFT_CFG_TMP_DIR, r_file)
                        local_file_deploy = os.path.join(settings.SWIFT_CFG_DEPLOY_DIR, r_file)
                        sftp_client.get(remote_file, local_file_tmp)
                        sftp_client.get(remote_file, local_file_deploy)

            except SSHException:
                ssh_client.close()
                logger.error('An error occurred restarting Swift nodes')
                raise FileSynchronizationException("An error occurred restarting Swift nodes")

            sftp_client.close()
            ssh_client.close()

        # 2nd step: load policies
        pattern = os.path.join(settings.SWIFT_CFG_TMP_DIR, 'object*')
        files = glob.glob(pattern)

        try:
            for builder_file in files:
                builder = RingBuilder.load(builder_file)
                if '-' in builder_file:
                    sp_id = builder_file.split('.')[0].split('-')[-1]
                    key = 'storage-policy:' + sp_id
                    if int(sp_id) > r.get('storage-policies:id'):
                        r.set('storage-policies:id', sp_id)
                else:
                    key = 'storage-policy:0'

                local_swift_file = get_swift_cfg_path(settings.SWIFT_CFG_DEPLOY_DIR)
                configParser = ConfigParser.RawConfigParser()
                configParser.read(local_swift_file)
                if configParser.has_section(key):

                    name = configParser.get(key, 'name') if configParser.has_option(key, 'name') else 'Policy-' + sp_id
                    policy_type = configParser.get(key, 'policy_type') if configParser.has_option(key, 'policy_type') else 'Replication'
                    deprecated = configParser.get(key, 'deprecated') if configParser.has_option(key, 'deprecated') else 'False'

                    if configParser.has_option(key, 'default'):
                        default = 'True' if configParser.get(key, 'default') in ['yes', 'Yes'] else 'False'
                    else:
                        default = 'False'

                    devices = []
                    nodes_data = {}
                    nodes = r.keys('*_node:*')
                    for node in nodes:
                        nodes_data[node] = r.hgetall(node)

                    for device in builder.devs:
                        try:
                            inet_aton(device['ip'])
                            device['ip'] = next((nodes_data[node]['name'] for node in nodes_data if nodes_data[node]['ip'] == device['ip']), device['ip'])
                        except:
                            pass
                        devices.append((device['ip'] + ':' + device['device'], device['id']))

                    data = {'name': name,
                            'default': default,
                            'deprecated': deprecated,
                            'time': builder.min_part_hours,
                            'devices': json.dumps(devices),
                            'deployed': 'True',
                            'policy_type': policy_type if policy_type else 'Replication',
                            'partition_power': int(math.log(builder.parts, 2)),
                            'replicas': int(builder.replicas)
                            }

                    r.hmset(key, data)

                else:
                    pass

        except RedisError:
                return JSONResponse('Policies could not be loaded', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse('Policies loaded correctly', status=status.HTTP_200_OK)

    return JSONResponse('Only HTTP POST requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def locality_list(request, account, container=None, swift_object=None):
    """
    Shows the nodes where the account/container/object is stored. In the case that
    the account/container/object does not exist, return the nodes where it will be save.
    """

    if request.method == 'GET':
        if not container:
            r = requests.get(settings.SWIFT_URL + "/endpoints/v2/" + account)
        elif not swift_object:
            r = requests.get(settings.SWIFT_URL + "/endpoints/v2/" + account + "/" + container)
        elif container and swift_object:
            r = requests.get(settings.SWIFT_URL + "/endpoints/v2/" + account + "/" + container + "/" + swift_object)
        return HttpResponse(r.content, content_type='application/json', status=r.status_code)
    return JSONResponse('Only HTTP GET /locality/ requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Node part
#
@csrf_exempt
def node_list(request):
    """
    GET: List all nodes ordered by name
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("*_node:*")
        nodes = []
        for key in keys:
            node = r.hgetall(key)
            node.pop("ssh_username", None)  # username & password are not returned in the list
            node.pop("ssh_password", None)
            node['devices'] = json.loads(node['devices'])

            r_id = node['region_id']
            z_id = node['zone_id']

            if r.exists('region:' + r_id):
                node['region_name'] = r.hgetall('region:' + r_id)['name']
            else:
                node['region_name'] = r_id

            if r.exists('zone:' + z_id):
                node['zone_name'] = r.hgetall('zone:' + z_id)['name']
            else:
                node['zone_name'] = z_id

            if 'ssh_access' not in node:
                node['ssh_access'] = False
            nodes.append(node)
        sorted_list = sorted(nodes, key=itemgetter('name'))
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def node_detail(request, server_type, node_id):
    """
    GET: Retrieve node details. PUT: Update node.
    :param request:
    :param server:
    :param node_id:
    :return:
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = server_type+"_node:" + node_id
    if request.method == 'GET':
        if r.exists(key):
            node = r.hgetall(key)
            node.pop("ssh_password", None)  # password is not returned
            node['devices'] = json.loads(node['devices'])
            return JSONResponse(node, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if r.exists(key):
            data = JSONParser().parse(request)
            try:
                ssh_user = data['ssh_username']
                ssh_password = data['ssh_password']
                node = r.hgetall(key)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh_client.connect(node['ip'], username=ssh_user, password=ssh_password)
                    ssh_client.close()
                    data['ssh_access'] = True
                except AuthenticationException:
                    data['ssh_access'] = False

                r.hmset(key, data)
                return JSONResponse("Node Data updated", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error updating node data", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        # Deletes the key. If the node is alive, the metric middleware will recreate this key again.
        if r.exists(key):
            node = r.delete(key)
            return JSONResponse('Node has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def node_restart(request, server_type, node_id):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = server_type+"_node:" + node_id
    logger.debug('Restarting node: ' + str(key))

    if request.method == 'PUT':
        node = r.hgetall(key)

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(node['ip'], username=node['ssh_username'], password=node['ssh_password'])

        try:
            ssh_client.exec_command('sudo swift-init main restart')
        except SSHException:
            ssh_client.close()
            logger.error('An error occurred restarting Swift nodes')
            raise FileSynchronizationException("An error occurred restarting Swift nodes")

        ssh_client.close()
        logger.debug('Node ' + str(key) + ' was restarted!')
        return JSONResponse('The node was restarted successfully.', status=status.HTTP_200_OK)

    logger.error('Method ' + str(request.method) + ' not allowed.')
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# Regions
@csrf_exempt
def regions(request):
    """
    GET: List all regions
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("region:*")
        region_items = []

        for key in keys:
            region = r.hgetall(key)
            region['id'] = key.split(':')[1]
            region_items.append(region)

        return JSONResponse(region_items, status=status.HTTP_200_OK)

    if request.method == 'POST':
        key = "region:" + str(r.incr('regions:id'))
        data = JSONParser().parse(request)
        try:
            r.hmset(key, data)
            return JSONResponse("Data inserted correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error inserting data", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def region_detail(request, region_id):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    regionKey = 'region:' + str(region_id)

    if request.method == 'GET':
        if r.exists(regionKey):
            region = r.hgetall(regionKey)
            return JSONResponse(region, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Region not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        # Deletes the key. If the node is alive, the metric middleware will recreate this key again.
        if r.exists(regionKey):
            keys = r.keys("zone:*")
            if 'zone:id' in keys:
                keys.remove('zone:id')
            for key in keys:
                zone = r.hgetall(key)
                if zone['region'] == region_id:
                    return JSONResponse("Region couldn't be deleted because the zone with id: " +
                                        region_id + ' has this region assigned.', status=status.HTTP_400_BAD_REQUEST)

            r.delete(regionKey)
            return JSONResponse('Region has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('Region not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        data = JSONParser().parse(request)
        key = "region:" + str(data['region_id'])
        try:
            r.hmset(key, data)
            return JSONResponse("Data updated correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# Zones
@csrf_exempt
def zones(request):
    """
    GET: List all zones
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("zone:*")
        zone_items = []

        for key in keys:
            zone = r.hgetall(key)
            zone['id'] = key.split(':')[1]
            zone['region_name'] = r.hgetall('region:' + zone['region'])['name']
            zone_items.append(zone)

        return JSONResponse(zone_items, status=status.HTTP_200_OK)

    if request.method == 'POST':
        key = "zone:" + str(r.incr('zones:id'))
        data = JSONParser().parse(request)
        try:
            r.hmset(key, data)
            return JSONResponse("Data inserted correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error inserting data", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def zone_detail(request, zone_id):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = 'zone:' + str(zone_id)

    if request.method == 'GET':
        if r.exists(key):
            zone = r.hgetall(key)
            return JSONResponse(zone, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Zone not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        # Deletes the key. If the node is alive, the metric middleware will recreate this key again.
        if r.exists(key):
            r.delete(key)
            return JSONResponse('Zone has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('Zone not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        data = JSONParser().parse(request)
        key = "zone:" + str(data['zone_id'])
        try:
            r.hmset(key, data)
            return JSONResponse("Zone Data updated correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error updating zone data", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# Containers
@csrf_exempt
def containers_list(request, project_id):
    if request.method == 'GET':
        token = get_token_connection(request)
        url = settings.SWIFT_URL + "/AUTH_" + project_id

        _, containers = swift_client.get_account(url, token)
        for c_id in reversed(range(len(containers))):
            if containers[c_id]['name'] in ('dependency', 'storlet'):
                del containers[c_id]

        return JSONResponse(containers, status=status.HTTP_200_OK)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)
