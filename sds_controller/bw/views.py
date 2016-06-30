import json

import redis
import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer


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
def bw_list(request):
    """
    List all slas, or create a SLA.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse("Error connecting with DB", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == "GET":

        headers = is_valid_request(request)
        if not headers:
            return JSONResponse("You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ", status=status.HTTP_401_UNAUTHORIZED)
        keystone_response = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)
        keystone_tenants = json.loads(keystone_response.content)["tenants"]

        tenants_list = {}
        for tenant in keystone_tenants:
            tenants_list[tenant["id"]] = tenant["name"]

        keys = r.keys("bw:AUTH_*")
        bw_limits = []
        for it in keys:
            for key, value in r.hgetall(it).items():
                policy_name = r.hget("storage-policy:" + key, "name")
                bw_limits.append({"tenant_id": it.replace("bw:AUTH_", ""), "tenant_name": tenants_list[it.replace("bw:AUTH_", "")], "policy_id": key, "policy_name": policy_name, "bandwidth": value})
        return JSONResponse(bw_limits, status=status.HTTP_200_OK)

    elif request.method == "POST":
        data = JSONParser().parse(request)
        try:
            r.hmset("bw:AUTH_" + str(data["tenant_id"]), {data["policy_id"]: data["bandwidth"]})
            return JSONResponse(data, status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error saving SLA.", status=status.HTTP_400_BAD_REQUEST)
    return JSONResponse("Method " + str(request.method) + " not allowed.", status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def bw_detail(request, tenant_key):
    """
    Retrieve, update or delete SLA.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse("Error connecting with DB", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    tenant_id = str(tenant_key).split(':')[0]
    policy_id = str(tenant_key).split(':')[1]

    if request.method == "GET":

        headers = is_valid_request(request)
        if not headers:
            return JSONResponse("You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ", status=status.HTTP_401_UNAUTHORIZED)
        keystone_response = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)
        keystone_tenants = json.loads(keystone_response.content)["tenants"]

        tenants_list = {}
        for tenant in keystone_tenants:
            tenants_list[tenant["id"]] = tenant["name"]

        bandwidth = r.hget("bw:AUTH_" + tenant_id, policy_id)
        policy_name = r.hget("storage-policy:" + policy_id, "name")
        sla = {"id": tenant_key, "tenant_id": tenant_id, "tenant_name": tenants_list[tenant_id], "policy_id": policy_id, "policy_name": policy_name, "bandwidth": bandwidth}
        return JSONResponse(sla, status=status.HTTP_200_OK)

    elif request.method == "PUT":
        data = JSONParser().parse(request)
        try:
            r.hmset("bw:AUTH_" + tenant_id, {policy_id: data["bandwidth"]})
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        r.hdel("bw:AUTH_" + tenant_id, policy_id)
        return JSONResponse("SLA has been deleted", status=status.HTTP_204_NO_CONTENT)
    return JSONResponse("Method " + str(request.method) + " not allowed.", status=status.HTTP_405_METHOD_NOT_ALLOWED)
