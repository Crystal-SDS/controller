import redis
import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

import sds_project
import storage_policy


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """

    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


def is_valid_request(request):
    headers = {}
    try:
        headers['X-Auth-Token'] = request.META['HTTP_X_AUTH_TOKEN']
        return headers
    except KeyError:
        return None


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


@csrf_exempt
def tenants_list(request):
    """
    List swift tenants.
    """
    if request.method == 'GET':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
        r = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)

        return HttpResponse(r.content, content_type='application/json', status=r.status_code)

    if request.method == "POST":
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
        data = JSONParser().parse(request)

        try:
            sds_project.add_new_sds_project(data["tenant_name"])
        except:
            return JSONResponse('Error creating a new project.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse('Account created successfully', status=status.HTTP_201_CREATED)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
        data = JSONParser().parse(request)
        storage_nodes_list = []
        if isinstance(data["storage_node"], dict):
            [storage_nodes_list.extend([k, v]) for k, v in data["storage_node"].items()]
            data["storage_node"] = ','.join(map(str, storage_nodes_list))
            try:
                storage_policy.create(data)
            except Exception as e:
                return JSONResponse('Error creating the Storage Policy: ' + e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JSONResponse('Account created successfully', status=status.HTTP_201_CREATED)
    return JSONResponse('Only HTTP POST /spolicies/ requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def locality_list(request, account, container=None, swift_object=None):
    """
    Shows the nodes where the account/container/object is stored. In the case that
    the account/container/object does not exist, return the nodes where it will be save.
    """
    if request.method == 'GET':
        if not container:
            r = requests.get(settings.SWIFT_URL + "endpoints/v2/" + account)
        elif not swift_object:
            r = requests.get(settings.SWIFT_URL + "endpoints/v2/" + account + "/" + container)
        elif container and swift_object:
            r = requests.get(settings.SWIFT_URL + "endpoints/v2/" + account + "/" + container + "/" + swift_object)
        return HttpResponse(r.content, content_type='application/json', status=r.status_code)
    return JSONResponse('Only HTTP GET /locality/ requests allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
def sort_detail(request, id):
    """
    Retrieve, update or delete a Proxy Sorting.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        proxy_sorting = r.hgetall("proxy_sorting:" + str(id))
        return JSONResponse(proxy_sorting, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
            r.hmset('proxy_sorting:' + str(id), data)
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except redis.exceptions.DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        r.delete("proxy_sorting:" + str(id))
        return JSONResponse('Proxy sorting has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)
