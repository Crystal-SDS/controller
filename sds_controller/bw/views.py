import redis
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer


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
        keys = r.keys("bw:AUTH_*")
        bw_limits = {}
        for key in keys:
            bw_limits[key] = r.hgetall(key)
        return JSONResponse(bw_limits, status=200)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            r.hmset('bw:AUTH_' + str(data['tenant']), {data['policy']: data['bandwidth']})
            return JSONResponse(data, status=201)
        except:
            return JSONResponse("Error saving SLA.", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def bw_detail(request, tenant_id):
    """
    Retrieve, update or delete SLA.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        sla = r.hgetall("bw:AUTH_" + str(tenant_id))
        return JSONResponse(sla, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('bw:AUTH_' + str(tenant_id), data)
            return JSONResponse("Data updated", status=201)
        except:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("bw:AUTH_" + str(tenant_id))
        return JSONResponse('SLA has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)
