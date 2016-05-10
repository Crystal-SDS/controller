from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
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


def proxyaddress():
    """
    Reads the proxy address from django settings.
    """
    return settings.SWIFT_URL + "/"


def is_valid_request(request):
    headers = {}
    try:
        headers['X-Auth-Token'] = request.META['HTTP_X_AUTH_TOKEN']
        return headers
    except:
        return None


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


# @csrf_exempt
# def bw_list_redis(request):
#     """
#     Ask the redis database information about the assigned BW to each
#     account and policy.
#     """
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself with the header X-Auth-Token ', status=401)
#     if request.method == 'GET':
#         keys = r.keys("bw:*")
#         bwdict = dict()
#         for key in keys:
#             bw = r.hgetall(key)
#             bwdict[key[3:]] = bw
#         return JSONResponse(bwdict, status=200)
#     return JSONResponse('Only HTTP GET /bw/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_detail_redis(request, account):
#     """
#     Ask the information of a certain tenant to redis.
#     """
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'GET':
#         bwdict = dict()
#         bwdict[account] = r.hgetall('bw:' + account)
#         return JSONResponse(bwdict, status=200)
#     return JSONResponse('Only HTTP GET /bw/<account>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_clear_all(request):
#     """
#     This call clears all the BW assignations for all accounts and policies.
#     """
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'PUT':
#         keys = r.keys("bw:*")
#         for key in keys:
#             r.delete(key)
#         return HttpResponse(request, status=200)
#     return JSONResponse('Only HTTP PUT /bw/clear/<account>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_clear_account(request, account):
#     """
#     This call clears all the BW assignations entries for the selected account.
#     """
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'PUT':
#         r.delete('bw:' + account)
#         return HttpResponse(request, status=200)
#     return JSONResponse('Only HTTP PUT /bw/clear/<account>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_clear_policy(request, account, policy):
#     """
#     This call clears all the BW assignations entries for the selected account
#     and policy.
#     """
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'PUT':
#         r.hdel('bw:' + account, policy)
#         return HttpResponse(request, status=200)
#     return JSONResponse('Only HTTP PUT /bw/clear/<account>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_update(request, account, bw_value):
#     '''
#     This call assigns the specified bw to all the policies of the selected
#     account
#     '''
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'PUT':
#         address = proxyaddress() + "bwmod/" + account + "/" + bw_value + "/"
#         r = requests.get(address, headers=headers)
#         return HttpResponse(r.content, content_type='application/json', status=r.status_code)
#     return JSONResponse('Only HTTP PUT /bw/<account>/<bw_value>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def bw_update_policy(request, account, policy, bw_value):
#     '''
#     This call assigns the specified bw to all the policies of the selected
#     account
#     '''
#     try:
#         r = get_redis_connection()
#     except:
#         return JSONResponse('Error connecting with DB', status=500)
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'PUT':
#         r.hset('bw:' + account, policy, bw_value)
#         return HttpResponse(request, status=200)
#     return JSONResponse('Only HTTP PUT /bw/clear/<account>/ requests allowed.', status=405)
#
#
# @csrf_exempt
# def osinfo(request):
#     """
#     Ask the proxy server information about the current objects and its BW.
#     """
#     headers = is_valid_request(request)
#     if not headers:
#         return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
#     if request.method == 'GET':
#         address = proxyaddress() + "osinfo/"
#         r = requests.get(address, headers=headers)
#         return HttpResponse(r.content, content_type='application/json', status=r.status_code)
#     return JSONResponse('Only HTTP GET /bw/osinfo/ requests allowed.', status=405)

############################################################################################

@csrf_exempt
def bw_list(request):
    """
    List all slas, or create a SLA.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("bw:*")
        bw_limits = {}
        for key in keys:
            bw_limits[key] = r.hgetall(key)
        return JSONResponse(bw_limits, status=200)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        dependency_id = r.incr("slas:id")
        try:
            data["id"] = dependency_id
            r.hmset('bw:' + str(dependency_id), data)
            return JSONResponse(data, status=201)
        except:
            return JSONResponse("Error saving SLA.", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def bw_detail(request, tenant):
    """
    Retrieve, update or delete SLA.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("bw:" + str(tenant))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('bw:' + str(tenant), data)
            return JSONResponse("Data updated", status=201)
        except:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("bw:" + str(tenant))
        return JSONResponse('SLA has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)