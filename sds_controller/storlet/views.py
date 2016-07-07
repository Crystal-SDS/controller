import hashlib
import json
import logging

import redis
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from swiftclient import client as swift_client
from swiftclient.exceptions import ClientException

from sds_controller.exceptions import SwiftClientError, StorletNotFoundException

# TODO create a common file and put this into the new file
# Start Common
STORLET_KEYS = ('id', 'filter_name', 'filter_type', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_put', 'is_get', 'has_reverse',
                'execution_server', 'execution_server_reverse', 'path')
DEPENDENCY_KEYS = ('id', 'name', 'version', 'permissions', 'path')

logging.basicConfig()


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


def check_keys(data, keys):
    return sorted(list(data)) == sorted(list(keys))


# End Common


@csrf_exempt
def storlet_list(request):
    """
    List all storlets, or create a new storlet.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'GET':
        keys = r.keys("filter:*")
        storlets = []
        for key in keys:
            storlet = r.hgetall(key)
            storlets.append(storlet)
        return JSONResponse(storlets, status=status.HTTP_200_OK)

    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if not check_keys(data.keys(), STORLET_KEYS[2:-1]):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        storlet_id = r.incr("filters:id")
        # TODO: Not needed?
        # if r.exists('filter:' + str(storlet_id)):
        #     return JSONResponse("Object already exists!", status=status.HTTP_409_CONFLICT)
        try:
            data['id'] = storlet_id
            r.hmset('filter:' + str(storlet_id), data)
            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storlet_detail(request, storlet_id):
    """
    Retrieve, update or delete a Storlet.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not r.exists("filter:" + str(storlet_id)):
        return JSONResponse('Object does not exist!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        storlet = r.hgetall("filter:" + str(storlet_id))
        return JSONResponse(storlet, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if not check_keys(data.keys(), STORLET_KEYS[2:-1]):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        try:
            r.hmset('filter:' + str(storlet_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            r.delete("filter:" + str(storlet_id))
            return JSONResponse('Filter has been deleted', status=status.HTTP_204_NO_CONTENT)
        except DataError:
            return JSONResponse("Error deleting filter", status=status.HTTP_408_REQUEST_TIMEOUT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class StorletData(APIView):
    """
    Upload or get a storlet data.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request, storlet_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=500)
        if r.exists("filter:" + str(storlet_id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.STORLET_DIR)
            md5_etag = md5(path)
            try:
                # r = get_redis_connection()
                r.hset("filter:" + str(storlet_id), "filter_name", str(path).split('/')[-1])
                r.hset("filter:" + str(storlet_id), "path", str(path))
                r.hset("filter:" + str(storlet_id), "content_length", str(request.META["CONTENT_LENGTH"]))
                r.hset("filter:" + str(storlet_id), "etag", str(md5_etag))
            except RedisError:
                return JSONResponse('Problems connecting with DB', status=500)
            return JSONResponse('Filter has been updated', status=201)
        return JSONResponse('Filter does not exist', status=404)

    def get(self, request, storlet_id, format=None):
        # TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)


@csrf_exempt
def storlet_deploy(request, storlet_id, account, container=None, swift_object=None):
    """
    Deploy a storlet to a specific swift account.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token.', status=status.HTTP_401_UNAUTHORIZED)
        storlet = r.hgetall("filter:" + str(storlet_id))

        if not storlet:
            return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)
        try:
            params = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        # Get an identifier of this new policy
        policy_id = r.incr("policies:id")

        # Set the policy data
        policy_data = {
            "policy_id": policy_id,
            "object_type": params['object_type'],
            "object_size": params['object_size'],
            "execution_order": policy_id,
            "params": params['params']
        }

        # TODO: Try to improve this part
        if container and swift_object:
            target = account + "/" + container + "/" + swift_object
        elif container:
            target = account + "/" + container
        else:
            target = account

        try:
            deploy(r, target, storlet, policy_data, headers)
            return JSONResponse('Successfully deployed.', status=status.HTTP_201_CREATED)
        except SwiftClientError:
            return JSONResponse('Error accessing Swift.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except StorletNotFoundException:
            return JSONResponse('Storlet not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storlet_list_deployed(request, account):
    """
    List all the storlets deployed.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        result = r.lrange("AUTH_" + str(account), 0, -1)
        if result:
            return JSONResponse(result, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Any Storlet deployed', status=status.HTTP_404_NOT_FOUND)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# @csrf_exempt
# def storlet_undeploy(request, storlet_id, account, container=None, swift_object=None):
#     """
#     Undeploy a storlet from a specific swift account.
#     """
#     try:
#         r = get_redis_connection()
#     except RedisError:
#         return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     storlet = r.hgetall("filter:" + str(storlet_id))
#     if not storlet:
#         return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)
#     if not r.exists("AUTH_" + str(account) + ":" + str(storlet["filter_name"])):
#         return JSONResponse('Filter ' + str(storlet["filter_name"]) + ' has not been deployed already', status=status.HTTP_404_NOT_FOUND)
#
#     if request.method == 'PUT':
#         headers = is_valid_request(request)
#         if not headers:
#             return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
#
#         if container and swift_object:
#             target = account + "/" + container + "/" + swift_object
#         elif container:
#             target = account + "/" + container
#         else:
#             target = account
#
#         return undeploy(r, target, storlet, headers)
#     return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ------------------------------
# DEPENDENCY PART
# ------------------------------


@csrf_exempt
def dependency_list(request):
    """
    List all dependencies, or create a Dependency.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("dependency:*")
        dependencies = []
        for key in keys:
            dependencies.append(r.hgetall(key))
        return JSONResponse(dependencies, status=200)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        dependency_id = r.incr("dependencies:id")
        try:
            data["id"] = dependency_id
            r.hmset('dependency:' + str(dependency_id), data)
            return JSONResponse(data, status=201)
        except DataError:
            return JSONResponse("Error to save the filter", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_detail(request, dependency_id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("dependency:" + str(dependency_id))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('dependency:' + str(dependency_id), data)
            return JSONResponse("Data updated", status=201)
        except DataError:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("dependency:" + str(dependency_id))
        return JSONResponse('Dependency has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


class DependencyData(APIView):
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request, dependency_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)
        if r.exists("dependency:" + str(dependency_id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.DEPENDENCY_DIR)
            r.hset("dependency:" + str(dependency_id), "path", str(path))
            return JSONResponse('Dependency has been updated', status=201)
        return JSONResponse('Dependency does not exist', status=404)

    def get(self, request, dependency_id, format=None):
        # TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)


@csrf_exempt
def dependency_deploy(request, dependency_id, account):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Problems to connect with the DB', status=500)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        dependency = r.hgetall("dependency:" + str(dependency_id))
        if not dependency:
            return JSONResponse('Dependency does not exist', status=404)
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency["version"])}

        if "path" not in dependency.keys():
            return JSONResponse('Dependency path does not exist', status=404)
        f = open(dependency["path"], 'r')
        content_length = None
        response = dict()
        try:
            swift_client.put_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(account), headers["X-Auth-Token"], 'dependency',
                                    dependency["name"], f, content_length, None, None, "application/octet-stream", metadata, None, None, None, response)
        except ClientException:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            f.close()
        status = response.get('status')
        if status == 201:
            if r.exists("AUTH_" + str(account) + ":dependency:" + str(dependency['name'])):
                return JSONResponse("Already deployed", status=200)

            if r.lpush("AUTH_" + str(account) + ":dependencies", str(dependency['name'])):
                return JSONResponse("Deployed", status=201)

        return JSONResponse("error", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_list_deployed(request, account):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Problems to connect with the DB', status=500)

    if request.method == 'GET':
        result = r.lrange("AUTH_" + str(account) + ":dependencies", 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_undeploy(request, dependency_id, account):
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Problems to connect with the DB', status=500)
    dependency = r.hgetall("dependency:" + str(dependency_id))

    if not dependency:
        return JSONResponse('Dependency does not exist', status=404)
    if not r.exists("AUTH_" + str(account) + ":dependency:" + str(dependency["name"])):
        return JSONResponse('Dependency ' + str(dependency["name"]) + ' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        try:
            swift_client.delete_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(account), headers["X-Auth-Token"],
                                       'dependency', dependency["name"], None, None, None, None, response)
        except ClientException:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        swift_status = response.get('status')
        if 200 <= swift_status < 300:
            r.delete("AUTH_" + str(account) + ":dependency:" + str(dependency["name"]))
            r.lrem("AUTH_" + str(account) + ":dependencies", str(dependency["name"]), 1)
            return JSONResponse('The dependency has been deleted', status=swift_status)
        return JSONResponse(response.get("reason"), status=swift_status)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


# FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 DO SET compression, SET caching
def deploy(r, target, storlet, parameters, headers):
    # print("Storlet ID: " + storlet["id"])
    # print("Storlet Details: " + str(r.hgetall("filter:" + storlet["id"])))
    # print("Target: " + target)
    # print("Params: " + str(parameters))

    if not parameters:
        parameters = {}

    target_list = target.split('/', 3)
    target = str(target).replace('/', ':')

    metadata = {"X-Object-Meta-Storlet-Language": storlet["filter_type"],
                "X-Object-Meta-Storlet-Interface-Version": storlet["interface_version"],
                "X-Object-Meta-Storlet-Dependency": storlet["dependencies"],
                "X-Object-Meta-Storlet-Object-Metadata": storlet["object_metadata"],
                "X-Object-Meta-Storlet-Main": storlet["main"]
                }

    storlet_path = storlet["path"]
    del storlet["path"]

    # try:
    storlet_file = open(storlet_path, 'r')
    # except IOError:
    #     return status.HTTP_404_NOT_FOUND

    # content_length = int(storlet["content_length"])
    # content_length = None
    swift_response = dict()

    # Change to API Call
    try:
        swift_client.put_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(target_list[0]),
                                headers["X-Auth-Token"], "storlet", storlet["filter_name"], storlet_file, None,
                                None, None, "application/octet-stream", metadata, None, None, None, swift_response)
    except ClientException as e:
        logging.error('Error in Swift put_object %s', e)
        raise SwiftClientError("A problem occurred accessing Swift")
    finally:
        storlet_file.close()

    swift_status = swift_response.get("status")

    if swift_status == status.HTTP_201_CREATED:
        # Change 'id' key of storlet
        storlet["filter_id"] = storlet.pop("id")
        # Get policy id
        policy_id = parameters["policy_id"]
        del parameters["policy_id"]
        # Add all storlet and policy metadata to policy_id in pipeline
        data = storlet.copy()
        data.update(parameters)

        data_dumped = json.dumps(data).replace('"True"', 'true').replace('"False"', 'false')

        r.hset("pipeline:AUTH_" + str(target), policy_id, data_dumped)
        # return status.HTTP_201_CREATED
    else:
        raise SwiftClientError("A problem occurred accessing Swift")
        # return status.HTTP_400_BAD_REQUEST


# FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 DO DELETE compression
def undeploy(r, target, storlet, headers):
    target_list = target.split('/', 3)
    swift_response = dict()
    try:
        swift_client.delete_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(target_list[0]),
                                   headers["X-Auth-Token"], "storlet", storlet["filter_name"], None, None, None, None, swift_response)
    except ClientException:
        return swift_response.get("status")

    swift_status = swift_response.get("status")

    if 200 <= swift_status < 300:
        keys = r.hgetall("pipeline:AUTH_" + str(target))
        for key, value in keys.items():
            json_value = json.loads(value)
            if json_value["filter_name"] == storlet["filter_name"]:
                r.hdel("pipeline:AUTH_" + str(target), key)
        return swift_status
    else:
        return swift_status


def save_file(file_, path=''):
    """
    Little helper to save a file
    """
    filename = file_._get_name()
    fd = open(str(path) + "/" + str(filename), 'wb')
    for chunk in file_.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) + "/" + str(filename)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
