from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.exceptions import ParseError
from rest_framework import status

from swiftclient import client as c
from rest_framework.views import APIView
from django.conf import settings
import redis
import hashlib

""" TODO create a common file and put this into the new file """
""" Start Common """
STORLET_KEYS = ('id', 'name', 'language', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_put', 'is_get', 'has_reverse', 'execution_server', 'execution_server_reverse', 'path')
DEPENDENCY_KEYS = ('id', 'name', 'version', 'permissions', 'path')


# Create your views here.

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
    except:
        return None


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


def check_keys(data, keys):
    return sorted(list(data)) == sorted(list(keys))


""" End Common """


@csrf_exempt
def storlet_list(request):
    """
    List all storlets, or create a new storlet.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'GET':
        keys = r.keys("storlet:*")
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

        if not check_keys(data.keys(), STORLET_KEYS[1:-1]):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        storlet_id = r.incr("storlets:id")
        # TODO: Not needed?
        # if r.exists('storlet:' + str(storlet_id)):
        #     return JSONResponse("Object already exists!", status=status.HTTP_409_CONFLICT)
        try:
            data['id'] = storlet_id
            r.hmset('storlet:' + str(storlet_id), data)
            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def storlet_detail(request, storlet_id):
    """
    Retrieve, update or delete a Storlet.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not r.exists("storlet:" + str(storlet_id)):
        return JSONResponse('Object does not exists!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        storlet = r.hgetall("storlet:" + str(storlet_id))
        return JSONResponse(storlet, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if not check_keys(data.keys(), STORLET_KEYS[1:-1]):
            print(data)
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        try:
            r.hmset('storlet:' + str(storlet_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            r.delete("storlet:" + str(storlet_id))
            return JSONResponse('Filter has been deleted', status=status.HTTP_204_NO_CONTENT)
        except:
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
        except:
            return JSONResponse('Error connecting with DB', status=500)
        if r.exists("storlet:" + str(storlet_id)):
            print 'request', request.META
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.STORLET_DIR)
            md5_etag = md5(path)
            try:
                r = get_redis_connection()
                result = r.hset("storlet:" + str(storlet_id), "path", str(path))
                result = r.hset("storlet:" + str(storlet_id), "content_length", str(request.META["CONTENT_LENGTH"]))
                result = r.hset("storlet:" + str(storlet_id), "etag", str(md5_etag))
            except:
                return JSONResponse('Problems connecting with DB', status=500)
            return JSONResponse('Filter has been updated', status=201)
        return JSONResponse('Filter does not exists', status=404)

    def get(self, request, storlet_id, format=None):
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Error connecting with DB', status=500)
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
    except:
        return JSONResponse('Problems to connect with the DB', status=500)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        storlet = r.hgetall("storlet:" + str(storlet_id))

        if not storlet:
            return JSONResponse('Filter does not exists', status=404)

        params = JSONParser().parse(request)

        # TODO: Try to improve this part
        if container and swift_object:
            target = account + "/" + container + "/" + swift_object
        elif container:
            target = account + "/" + container
        else:
            target = account

        return deploy(r, storlet, target, params, headers)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def storlet_list_deployed(request, account):
    """
    List all the storlets deployed.
    """
    if request.method == 'GET':
        r = get_redis_connection()
        result = r.lrange("AUTH_" + str(account), 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def storlet_undeploy(request, storlet_id, account, container=None, swift_object=None):
    """
    Undeploy a storlet from a specific swift account.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Problems to connect with the DB', status=500)
    storlet = r.hgetall("storlet:" + str(storlet_id))
    if not storlet:
        return JSONResponse('Filter does not exists', status=404)
    if not r.exists("AUTH_" + str(account) + ":" + str(storlet["name"])):
        return JSONResponse('Filter ' + str(storlet["name"]) + ' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        if container and swift_object:
            target = account + "/" + container + "/" + swift_object
        elif container:
            target = account + "/" + container
        else:
            target = account

        return undeploy(r, storlet, target, headers)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


"""
------------------------------
DEPENDENCY PART
------------------------------
"""


@csrf_exempt
def dependency_list(request):
    """
    List all dependencies, or create a Dependency.
    """
    try:
        r = get_redis_connection()
    except:
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
        except:
            return JSONResponse("Error to save the filter", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_detail(request, dependency_id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("dependency:" + str(dependency_id))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('dependency:' + str(dependency_id), data)
            return JSONResponse("Data updated", status=201)
        except:
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
        except:
            return JSONResponse('Problems to connect with the DB', status=500)
        if r.exists("dependency:" + str(dependency_id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.DEPENDENCY_DIR)
            try:
                r = get_redis_connection()
                result = r.hset("dependency:" + str(dependency_id), "path", str(path))
            except:
                return JSONResponse('Problems connecting with DB', status=500)
            return JSONResponse('Dependency has been updated', status=201)
        return JSONResponse('Dependency does not exists', status=404)

    def get(self, request, dependency_id, format=None):
        # TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)


@csrf_exempt
def dependency_deploy(request, dependency_id, account):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Problems to connect with the DB', status=500)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        dependency = r.hgetall("dependency:" + str(dependency_id))
        if not dependency:
            return JSONResponse('Dependency does not exists', status=404)
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency["version"])}

        if "path" not in dependency.keys():
            return JSONResponse('Dependency path does not exists', status=404)
        f = open(dependency["path"], 'r')
        content_length = None
        response = dict()
        try:
            c.put_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(account), headers["X-Auth-Token"], 'dependency', dependency["name"], f,
                         content_length, None, None, "application/octet-stream",
                         metadata, None, None, None, response)
        except:
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
    if request.method == 'GET':
        r = get_redis_connection()
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
    except:
        return JSONResponse('Problems to connect with the DB', status=500)
    dependency = r.hgetall("dependency:" + str(dependency_id))

    if not dependency:
        return JSONResponse('Dependency does not exists', status=404)
    if not r.exists("AUTH_" + str(account) + ":dependency:" + str(dependency["name"])):
        return JSONResponse('Dependency ' + str(dependency["name"]) + ' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        try:
            c.delete_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(account), headers["X-Auth-Token"],
                            'dependency', dependency["name"], None, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        status = response.get('status')
        if 200 <= status < 300:
            r.delete("AUTH_" + str(account) + ":dependency:" + str(dependency["name"]))
            r.lrem("AUTH_" + str(account) + ":dependencies", str(dependency["name"]), 1)
            return JSONResponse('The dependency has been deleted', status=status)
        return JSONResponse(response.get("reason"), status=status)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


def deploy(r, storlet, target, params, headers):
    print 'into deploy', params
    if not params:
        params = {}
    target_list = target.split('/', 3)

    metadata = {'X-Object-Meta-Storlet-Language': 'Java',
                'X-Object-Meta-Storlet-Interface-Version': '1.0',
                'X-Object-Meta-Storlet-Dependency': storlet['dependencies'],
                'X-Object-Meta-Storlet-Object-Metadata': 'no',
                'X-Object-Meta-Storlet-Main': storlet['main']}
    try:
        f = open(storlet['path'], 'r')
    except:
        return JSONResponse('Not found the filter data file', status=404)
    
    content_length = None
    response = dict()
    # Change to API Call
    try:
        print storlet['name']
        print "token", headers["X-Auth-Token"]
        c.put_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(target_list[0]), headers["X-Auth-Token"], 'storlet', storlet['name'], f,
                     content_length, None, None,
                     "application/octet-stream", metadata,
                     None, None, None, response)
    except:
        print 'response put', response.get("reason")
        return JSONResponse(response.get("reason"), status=response.get('status'))
    finally:
        f.close()
    print 'response', response
    status = response.get('status')
    if status == 201:
        if r.exists("AUTH_"+str(target)+":"+str(storlet['name'])):
            return JSONResponse("Already deployed", status=400)
        if r.lpush("pipeline:AUTH_"+str(target), str(storlet['name'])):
                params["id"] = storlet["id"]
                print 'params', params
                if not "params" in params.keys():
                    params["params"] = ""
                if r.hmset("AUTH_"+str(target)+":"+str(storlet['name']), params):
                    return JSONResponse("Deployed", status=201)
                else:
                    print 'Error setting redis on deploy Storlet'

    return JSONResponse("error", status=400)


def undeploy(r, storlet, target, headers):
    target_list = target.split('/', 3)
    response = dict()
    try:
        c.delete_object(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/" + "AUTH_" + str(target_list[0]), 
                        headers["X-Auth-Token"], 'storlet', storlet["name"], None, None, None, None, response)
    except:
        pass
    print 'Swift response: ', response
    status = response.get('status')
    if 200 <= status < 300:
        r.delete("AUTH_" + str(target) + ":" + str(storlet["name"]))
        r.lrem("pipeline:AUTH_" + str(target), str(storlet["name"]), 1)
        return JSONResponse('The object has been deleted', status=status)
    return JSONResponse(response.get("reason"), status=status)


def save_file(file_, path=''):
    '''
    Little helper to save a file
    '''
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
