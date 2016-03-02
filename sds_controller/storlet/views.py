from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser, FormParser

from swiftclient import client as c
from rest_framework.views import APIView
from django.conf import settings
import redis
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

@csrf_exempt
def storlet_list(request):
    """
    List all storlets, or create a new storlet.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'GET':
        keys = r.keys("storlet:*")
        storlets = []
        for key in keys:
            storlet = r.hgetall(key)
            storlets.append(storlet)
        return JSONResponse(storlets, status=200)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        storlet_id = r.incr("storlets:id")
        try:
            data["id"] = storlet_id
            r.hmset('storlet:'+str(storlet_id), data)
            return JSONResponse(data, status=201)
        except:
            return JSONResponse("Error to save the object", status=400)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def storlet_detail(request, id):
    """
    Retrieve, update or delete a Storlet.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        storlet = r.hgetall("storlet:"+str(id))
        return JSONResponse(storlet, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('storlet:'+str(id), data)
            return JSONResponse("Data updated", status=201)
        except:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("storlet:"+str(id))
        return JSONResponse('Filter has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

class StorletData(APIView):
    """
    Upload or get a storlet data.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request, id, format=None):
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Error connecting with DB', status=500)
        if r.exists("storlet:"+str(id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.STORLET_DIR)
            try:
                r = get_redis_connection()
                result = r.hset("storlet:"+str(id), "path", str(path))
            except:
                return JSONResponse('Problems connecting with DB', status=500)
            return JSONResponse('Filter has been updated', status=201)
        return JSONResponse('Filter does not exists', status=404)
    def get(self, request, id, format=None):
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Error connecting with DB', status=500)
        #TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)

@csrf_exempt
def storlet_deploy(request, id, account):
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
        storlet = r.hgetall("storlet:"+str(id))
        if not storlet:
            return JSONResponse('Filter does not exists', status=404)
        params = JSONParser().parse(request)
        print 'params', params
        return deploy(r, storlet, account, params, headers)

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def storlet_list_deployed(request, account):
    """
    List all the storlets deployed.
    """
    if request.method == 'GET':
        r = get_redis_connection()
        result = r.lrange("AUTH_"+str(account), 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def storlet_undeploy(request, id, account):
    """
    Undeploy a storlet from a specific swift account.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Problems to connect with the DB', status=500)
    storlet = r.hgetall("storlet:"+str(id))
    if not storlet:
        return JSONResponse('Filter does not exists', status=404)
    if not r.exists("AUTH_"+str(account)+":"+str(storlet["name"])):
        return JSONResponse('Filter '+str(storlet["name"])+' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
	return undeploy(r, storlet, account, headers)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

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
            r.hmset('dependency:'+str(dependency_id), data)
            return JSONResponse(data, status=201)
        except:
            return JSONResponse("Error to save the filter", status=400)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_detail(request, id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("dependency:"+str(id))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('dependency:'+str(id), data)
            return JSONResponse("Data updated", status=201)
        except:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("dependency:"+str(id))
        return JSONResponse('Dependency has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

class DependencyData(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    def put(self, request, id, format=None):
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Problems to connect with the DB', status=500)
        if r.exists("dependency:"+str(id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.DEPENDENCY_DIR)
            try:
                r = get_redis_connection()
                result = r.hset("dependency:"+str(id), "path", str(path))
            except:
                return JSONResponse('Problems connecting with DB', status=500)
            return JSONResponse('Dependency has been updated', status=201)
        return JSONResponse('Dependency does not exists', status=404)

    def get(self, request, id, format=None):
        #TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)



@csrf_exempt
def dependency_deploy(request, id, account):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Problems to connect with the DB', status=500)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        dependency = r.hgetall("dependency:"+str(id))
        if not dependency:
            return JSONResponse('Dependency does not exists', status=404)
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency["version"])}
        f = open(dependency["path"],'r')
        content_length = None
        response = dict()
        try:
            c.put_object(settings.SWIFT_URL+settings.SWIFT_API_VERSION+"/"+"AUTH_"+str(account), headers["X-Auth-Token"], 'dependency', dependency["name"], f,
                         content_length, None, None, "application/octet-stream",
                         metadata, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            f.close()
        status = response.get('status')
        if status == 201:
            if r.exists("AUTH_"+str(account)+":dependency:"+str(dependency['name'])):
                return JSONResponse("Already deployed", status=200)

            if r.lpush("AUTH_"+str(account)+":dependencies", str(dependency['name'])):
                r.set("AUTH_"+str(account)+":dependency:"+str(dependency['name']), 1)
                return JSONResponse("Deployed", status=201)

        return JSONResponse("error", status=400)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_list_deployed(request, account):

    if request.method == 'GET':
        r = get_redis_connection()
        result = r.lrange("AUTH_"+str(account)+":dependencies", 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_undeploy(request, id, account):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Problems to connect with the DB', status=500)
    dependency = r.hgetall("dependency:"+str(id))

    if not dependency:
        return JSONResponse('Dependency does not exists', status=404)
    if not r.exists("AUTH_"+str(account)+":dependency:"+str(dependency["name"])):
        return JSONResponse('Dependency '+str(dependency["name"])+' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        try:
            c.delete_object(settings.SWIFT_URL+settings.SWIFT_API_VERSION+"/"+"AUTH_"+str(account),headers["X-Auth-Token"],
                'dependency', dependency["name"], None, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        status = response.get('status')
        if 200 <= status < 300:
            r.delete("AUTH_"+str(account)+":dependency:"+str(dependency["name"]))
            r.lrem("AUTH_"+str(account)+":dependencies", str(dependency["name"]), 1)
            return JSONResponse('The dependency has been deleted', status=status)
        return JSONResponse(response.get("reason"), status=status)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

def deploy(r, storlet, account, params, headers):
    metadata = {'X-Object-Meta-Storlet-Language':'Java',
        'X-Object-Meta-Storlet-Interface-Version':'1.0',
        'X-Object-Meta-Storlet-Dependency': storlet['dependencies'],
        'X-Object-Meta-Storlet-Object-Metadata':'no',
        'X-Object-Meta-Storlet-Main': storlet['main']}
    try:
        f = open(storlet['path'],'r')
    except:
        return JSONResponse('Not found the filter data file', status=404)
    content_length = None
    response = dict()
    #Change to API Call
    try:
        print storlet['name']
        print "token", headers["X-Auth-Token"]
        c.put_object(settings.SWIFT_URL+settings.SWIFT_API_VERSION+"/"+"AUTH_"+str(account), headers["X-Auth-Token"], 'storlet', storlet['name'], f,
                     content_length, None, None,
                     "application/octet-stream", metadata,
                     None, None, None, response)
    except:
        return JSONResponse(response.get("reason"), status=response.get('status'))
    finally:
        f.close()
    status = response.get('status')
    if status == 201:
        if r.exists("AUTH_"+str(account)+":"+str(storlet['name'])):
            return JSONResponse("Already deployed", status=200)
        if r.lpush("AUTH_"+str(account), str(storlet['name'])):
                params["storlet_id"] = storlet["id"]
                if r.hmset("AUTH_"+str(account)+":"+str(storlet['name']), params):
                    return JSONResponse("Deployed", status=201)
    return JSONResponse("error", status=400)

def undeploy(r, storlet, account, headers):
    response = dict()
    try:
        c.delete_object(settings.SWIFT_URL+settings.SWIFT_API_VERSION+"/"+"AUTH_"+str(account),headers["X-Auth-Token"],
            'storlet', storlet["name"], None, None, None, None, response)
        print 'response, ', response
    except:
        return JSONResponse(response.get("reason"), status=response.get('status'))
    status = response.get('status')
    if 200 <= status < 300:
        r.delete("AUTH_"+str(account)+":"+str(storlet["name"]))
        r.lrem("AUTH_"+str(account), str(storlet["name"]), 1)
        return JSONResponse('The object has been deleted', status=status)
    return JSONResponse(response.get("reason"), status=status)

def save_file(file, path=''):
    '''
    Little helper to save a file
    '''
    filename = file._get_name()
    fd = open(str(path) +"/"+ str(filename), 'wb')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) +"/"+ str(filename)
