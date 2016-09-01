from operator import itemgetter
from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from swiftclient import client as swift_client
from swiftclient.exceptions import ClientException

from sds_controller.exceptions import SwiftClientError, StorletNotFoundException, FileSynchronizationException
from sds_controller.common_utils import rsync_dir_with_nodes, to_json_bools, JSONResponse, get_redis_connection, is_valid_request

import errno
import hashlib
import json
import logging
import mimetypes
import os

# TODO create a common file and put this into the new file
# Start Common
STORLET_KEYS = ('id', 'filter_name', 'filter_type', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_put', 'is_get', 'has_reverse',
                'execution_server', 'execution_server_reverse', 'path')
NATIVE_FILTER_KEYS = ('id', 'filter_name', 'filter_type', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_pre_put', 'is_post_put',
                      'is_pre_get', 'is_post_get', 'has_reverse', 'execution_server', 'execution_server_reverse', 'path')
DEPENDENCY_KEYS = ('id', 'name', 'version', 'permissions', 'path')

logging.basicConfig()

def check_keys(data, keys):
    return sorted(list(data)) == sorted(list(keys))
# End Common


@csrf_exempt
def storlet_list(request):
    """
    List all storlets, or create a new storlet.
    """
    # Validate request: only Crystal admin user can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
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
        sorted_list = sorted(storlets, key=lambda x: int(itemgetter("id")(x)))
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)

    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if (('filter_type' not in data) or
                (data['filter_type'] == 'storlet' and not check_keys(data.keys(), STORLET_KEYS[2:-1])) or
                (data['filter_type'] == 'native' and not check_keys(data.keys(), NATIVE_FILTER_KEYS[2:-1]))):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        storlet_id = r.incr("filters:id")
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
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not r.exists("filter:" + str(storlet_id)):
        return JSONResponse('Object does not exist!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        storlet = r.hgetall("filter:" + str(storlet_id))

        to_json_bools(storlet, 'is_get', 'is_put', 'has_reverse')
        return JSONResponse(storlet, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if (('filter_type' not in data) or
                (data['filter_type'] == 'storlet' and not check_keys(data.keys(), STORLET_KEYS[3:-1])) or
                (data['filter_type'] == 'native' and not check_keys(data.keys(), NATIVE_FILTER_KEYS[3:-1]))):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        try:
            r.hmset('filter:' + str(storlet_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            keys = r.keys('dsl_filter:*')
            for key in keys:
                dsl_filter_id = r.hget(key, 'identifier')
                if dsl_filter_id == storlet_id:
                    return JSONResponse('Unable to delete filter, is in use by the Registry DSL.', status=status.HTTP_403_FORBIDDEN)

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
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        filter_name = "filter:" + str(storlet_id)
        if r.exists(filter_name):
            file_obj = request.FILES['file']

            filter_type = r.hget(filter_name, 'filter_type')
            if (filter_type == 'storlet' and not file_obj.name.endswith('.jar')) or \
                    (filter_type == 'native' and not file_obj.name.endswith('.py')):
                return JSONResponse('Uploaded file is incompatible with filter type', status=status.HTTP_400_BAD_REQUEST)
            if filter_type == 'storlet':
                filter_dir = settings.STORLET_FILTERS_DIR
            else:
                filter_dir = settings.NATIVE_FILTERS_DIR
            make_sure_path_exists(filter_dir)
            path = save_file(file_obj, filter_dir)
            md5_etag = md5(path)

            try:
                r.hset(filter_name, "filter_name", os.path.basename(path))
                r.hset(filter_name, "path", str(path))
                r.hset(filter_name, "content_length", str(request.META["CONTENT_LENGTH"]))
                r.hset(filter_name, "etag", str(md5_etag))
            except RedisError:
                return JSONResponse('Problems connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if filter_type == 'native':
                # synchronize metrics directory with all nodes
                try:
                    rsync_dir_with_nodes(filter_dir)
                except FileSynchronizationException as e:
                    return JSONResponse(e.message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return JSONResponse('Filter has been updated', status=status.HTTP_201_CREATED)
        return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)

    def get(self, request, storlet_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('filter:' + str(storlet_id)):
            filter_path = r.hget('filter:' + str(storlet_id), 'path')
            if os.path.exists(filter_path):
                filter_name = os.path.basename(filter_path)
                filter_size = os.stat(filter_path).st_size

                # Generate response
                response = StreamingHttpResponse(FileWrapper(open(filter_path), filter_size), content_type=mimetypes.guess_type(filter_path)[0])
                response['Content-Length'] = filter_size
                response['Content-Disposition'] = "attachment; filename=%s" % filter_name

                return response
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
def filter_deploy(request, filter_id, account, container=None, swift_object=None):
    """
    Deploy a filter to a specific swift account.
    """
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
              
        filter_data = r.hgetall("filter:" + str(filter_id))

        if not filter_data:
            return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)
        
        try:
            params = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request params", status=status.HTTP_400_BAD_REQUEST)

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
            set_filter(r, target, filter_data, policy_data, token)
            return JSONResponse(policy_id, status=status.HTTP_201_CREATED)
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
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'GET':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        result = r.lrange("AUTH_" + str(account), 0, -1)
        if result:
            return JSONResponse(result, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Any Storlet deployed', status=status.HTTP_404_NOT_FOUND)
        
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def filter_undeploy(request, filter_id, account, container=None, swift_object=None):
    """
    Undeploy a storlet from a specific swift account.
    """
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
         
        filter_data = r.hgetall("filter:" + str(filter_id))
         
        if not filter_data:
            return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)
         
        if not r.exists("AUTH_" + str(account) + ":" + str(filter_data["filter_name"])):
            return JSONResponse('Filter ' + str(filter_data["filter_name"]) + ' has not been deployed already', status=status.HTTP_404_NOT_FOUND)

        if container and swift_object:
            target = account + "/" + container + "/" + swift_object
        elif container:
            target = account + "/" + container
        else:
            target = account
 
        print target
         
        return unset_filter(r, target, filter_data, token)
     
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ------------------------------
# DEPENDENCY PART
# ------------------------------


@csrf_exempt
def dependency_list(request):
    """
    List all dependencies, or create a Dependency.
    """
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
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
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
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

    # Validate request: only Crystal admin user can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=401)
    
    if request.method == 'PUT':   
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)
        
        dependency = r.hgetall("dependency:" + str(dependency_id))
        if not dependency:
            return JSONResponse('Dependency does not exist', status=404)
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency["version"])}

        if "path" not in dependency.keys():
            return JSONResponse('Dependency path does not exist', status=404)

        try:
            dependency_file = open(dependency["path"], 'r')
            content_length = None
            response = dict()
            url = settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_" + str(account)
            swift_client.put_object(url, token, 'dependency', dependency["name"], dependency_file, content_length,  
                                    None, None, "application/octet-stream", metadata, None, None, None, response)
        except ClientException:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            dependency_file.close()
            
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
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'GET':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)
        
        result = r.lrange("AUTH_" + str(account) + ":dependencies", 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
        
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_undeploy(request, dependency_id, account):
    """ Validate request: only Crystal admin user can access to this method """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)
        
        dependency = r.hgetall("dependency:" + str(dependency_id))
    
        if not dependency:
            return JSONResponse('Dependency does not exist', status=404)
        if not r.exists("AUTH_" + str(account) + ":dependency:" + str(dependency["name"])):
            return JSONResponse('Dependency ' + str(dependency["name"]) + ' has not been deployed already', status=404)

        try:
            response = dict()
            url = settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_" + str(account)
            swift_client.delete_object(url, token,'dependency', dependency["name"], None, None, None, None, response)
        except ClientException:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        
        swift_status = response.get('status')
        
        if 200 <= swift_status < 300:
            r.delete("AUTH_" + str(account) + ":dependency:" + str(dependency["name"]))
            r.lrem("AUTH_" + str(account) + ":dependencies", str(dependency["name"]), 1)
            return JSONResponse('The dependency has been deleted', status=swift_status)
        
        return JSONResponse(response.get("reason"), status=swift_status)
    
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)

def set_filter(r, target, filter_data, parameters, token):
    
    if filter_data['filter_type'] == 'storlet':
        metadata = {"X-Object-Meta-Storlet-Language": 'java',
            "X-Object-Meta-Storlet-Interface-Version": filter_data["interface_version"],
            "X-Object-Meta-Storlet-Dependency": filter_data["dependencies"],
            "X-Object-Meta-Storlet-Object-Metadata": filter_data["object_metadata"],
            "X-Object-Meta-Storlet-Main": filter_data["main"]
            }
            
        target_list = target.split('/', 3)
        url = settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_" + str(target_list[0])
        swift_response = dict()
        
        print token, 
        try:
            storlet_file = open(filter_data["path"], 'r')
            swift_client.put_object(url, token, "storlet", filter_data["filter_name"], storlet_file, None,
                                    None, None, "application/octet-stream", metadata, None, None, None, swift_response)
        except ClientException as e:
            logging.error(str(e))
            raise SwiftClientError("A problem occurred accessing Swift")
        
        finally:
            storlet_file.close()
    
        swift_status = swift_response.get("status")
    
        if swift_status != status.HTTP_201_CREATED:
            raise SwiftClientError("A problem occurred uploading Storlet to Swift")


    if not parameters:
        parameters = {}

    target = str(target).replace('/', ':')
    # Change 'id' key of filter
    filter_data["filter_id"] = filter_data.pop("id")
    # Get policy id
    policy_id = parameters["policy_id"]
    
    del filter_data["path"]
    del parameters["policy_id"]
    # Add all filter and policy metadata to policy_id in pipeline
    data = filter_data.copy()
    data.update(parameters)

    data_dumped = json.dumps(data).replace('"True"', 'true').replace('"False"', 'false')

    r.hset("pipeline:AUTH_" + str(target), policy_id, data_dumped)


# FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 DO DELETE compression
def unset_filter(r, target, filter_data, token):
    swift_response = dict()
    if filter_data['filter_type'] == 'storlet':
        try:
            target_list = target.split('/', 3)
            url = settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_" + str(target_list[0]) 
            swift_client.delete_object(url, token, "storlet", filter_data["filter_name"], None, None, None, None, swift_response)
        except ClientException as e:
            print swift_response+str(e)
            return swift_response.get("status")

    keys = r.hgetall("pipeline:AUTH_" + str(target))
    for key, value in keys.items():
        json_value = json.loads(value)
        if json_value["filter_name"] == filter_data["filter_name"]:
            r.hdel("pipeline:AUTH_" + str(target), key)

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def save_file(file_, path=''):
    """
    Little helper to save a file
    """
    filename = file_.name
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
