import json
import logging
import redis
import requests
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from operator import itemgetter

import sds_project
import storage_policies_utils
from api.common_utils import JSONResponse, get_redis_connection, get_token_connection
from api.exceptions import FileSynchronizationException

logger = logging.getLogger(__name__)


#
# Storage Policy
#

@csrf_exempt
def storage_policy_list(request):
    """
    List all storage policies.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'GET':
        keys = r.keys("storage-policy:*")
        storage_policy_list = []
        for key in keys:
            storage_policy = r.hgetall(key)
            storage_policy['id'] = str(key).split(':')[-1]
            storage_policy_list.append(storage_policy)
        return JSONResponse(storage_policy_list, status=status.HTTP_200_OK)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storage_policies(request):
    """
    Creates a storage policy to swift with an specific ring.
    Allows create replication storage policies and erasure code storage policies
    """

    if request.method == "POST":
        data = JSONParser().parse(request)
        storage_nodes_list = []
        if isinstance(data["storage_node"], dict):
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
                return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)
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
    GET: List all regions ordered by name
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("region:*")
        if 'region:id' in keys:
            keys.remove('region:id')

        region_items = []

        for key in keys:
            region = r.hgetall(key)
            region['id'] = key.split(':')[1]
            region_items.append(region)

        sorted_list = sorted(region_items, key=itemgetter('name'))
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)

    if request.method == 'POST':
        key = "region:" + str(r.incr('region:id'))
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

    key = 'region:' + str(region_id)
    if request.method == 'DELETE':
        # Deletes the key. If the node is alive, the metric middleware will recreate this key again.
        if r.exists(key):
            r.delete(key)
            return JSONResponse('Node has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if r.exists(key):
            region = r.hgetall(key)
            return JSONResponse(region, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Region not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)

#
# PROXY SORTING NOT USED, TODO: Remove
#

@csrf_exempt
def sort_list(request):
    """
    List all proxy sortings, or create a proxy sortings.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("proxy_sorting:*")
        proxy_sortings = []
        for key in keys:
            proxy_sortings.append(r.hgetall(key))
        return JSONResponse(proxy_sortings, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            if not data:
                return JSONResponse("Empty request", status=status.HTTP_400_BAD_REQUEST)

            proxy_sorting_id = r.incr("proxies_sorting:id")
            data["id"] = proxy_sorting_id
            r.hmset('proxy_sorting:' + str(proxy_sorting_id), data)
            return JSONResponse(data, status=status.HTTP_201_CREATED)
        except redis.exceptions.DataError:
            return JSONResponse("Error to save the proxy sorting", status=status.HTTP_400_BAD_REQUEST)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def sort_detail(request, sort_id):
    """
    Retrieve, update or delete a Proxy Sorting.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        proxy_sorting = r.hgetall("proxy_sorting:" + str(sort_id))
        return JSONResponse(proxy_sorting, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
            r.hmset('proxy_sorting:' + str(sort_id), data)
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except redis.exceptions.DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        r.delete("proxy_sorting:" + str(sort_id))
        return JSONResponse('Proxy sorting has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)

