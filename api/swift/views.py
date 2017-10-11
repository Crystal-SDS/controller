from paramiko.ssh_exception import SSHException, AuthenticationException
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from operator import itemgetter
import json
import logging
import requests
import paramiko
import storage_policies_utils
from api.common_utils import JSONResponse, get_redis_connection
from api.exceptions import FileSynchronizationException

logger = logging.getLogger(__name__)


#
# Storage Policies
#
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
            storage_policy['id'] = str(key).split(':')[-1]
            storage_policy_list.append(storage_policy)
        return JSONResponse(storage_policy_list, status=status.HTTP_200_OK)

    if request.method == "POST":
        data = JSONParser().parse(request)
        storage_nodes_list = []
        if isinstance(data["storage_node"], dict):
            data['storage_node']['policy_id'] = r.incr('storage-policies:id')
            for k, v in data["storage_node"].items():
                storage_nodes_list.extend([k, v])
            data["storage_node"] = ','.join(map(str, storage_nodes_list))
            try:
                storage_policies_utils.create(data)
            except Exception as e:
                return JSONResponse('Error creating the Storage Policy: ' + e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            storage_policy['devices'] = json.loads(storage_policy['devices'])
            return JSONResponse(storage_policy, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if r.exists(key):
            data = JSONParser().parse(request)
            try:
                r.hmset(key, data)
                return JSONResponse("Storage Policy updated", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error updating storage policy", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Storage policy not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
