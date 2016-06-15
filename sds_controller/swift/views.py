from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
import storage_policy
import sds_project
import requests
import redis


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
def tenants_list(request):
    """
    List swift tenants.
    """
    if request.method == 'GET':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        r = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)
        print "---"
        print r
        return HttpResponse(r.content, content_type='application/json', status=r.status_code)

    if request.method == "POST":
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        data = JSONParser().parse(request)
        
        try:
            sds_project.add_new_sds_project(data["tenant_name"])
        except:
            return JSONResponse('Error creating a new project.', status=500)
        
        return JSONResponse('Account created successfully', status=201)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)


@csrf_exempt
def storage_policies(request):
    """
    Creates a storage policy to swift with an specific ring.
    Allows create replication storage policies and erasure code storage policies
    """
    if request.method == "POST":
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        data = JSONParser().parse(request)
        storage_nodes_list = []
        if isinstance(data["storage_node"], dict):
            [storage_nodes_list.extend([k, v]) for k, v in data["storage_node"].items()]
            data["storage_node"] = ','.join(map(str, storage_nodes_list))
            try:
                storage_policy.create(data)
            except Exception as e:
                return JSONResponse('Error creating the Storage Policy: '+e, status=500)
            
        return JSONResponse('Account created successfully', status=201)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)


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
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)


@csrf_exempt
def sort_list(request):
    """
    List all dependencies, or create a Dependency.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("proxy_sorting:*")
        dependencies = []
        for key in keys:
            dependencies.append(r.hgetall(key))
        return JSONResponse(dependencies, status=200)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        dependency_id = r.incr("proxies_sorting:id")
        try:
            data["id"] = dependency_id
            r.hmset('proxy_sorting:' + str(dependency_id), data)
            return JSONResponse(data, status=201)
        except:
            return JSONResponse("Error to save the proxy sorting", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def sort_detail(request, id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("proxy_sorting:" + str(id))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('proxy_sorting:' + str(id), data)
            return JSONResponse("Data updated", status=201)
        except:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("proxy_sorting:" + str(id))
        return JSONResponse('Proxy sorting has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)
