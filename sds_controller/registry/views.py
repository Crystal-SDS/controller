from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from django.conf import settings
import redis
import json

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)

"""
Metric Workload part
"""
@csrf_exempt
def add_metric(request):
    """
    Add a metric workload in the registry (redis)
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("metric:*")
        print 'keys', keys
        metrics = []
        for key in keys:
            metric = r.hgetall(key)
            metric["name"]=key.split(":")[1]
            metrics.append(metric)
        return JSONResponse(metrics, status=200)
    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Metric must have a name', status=400)
        r.hmset('metric:'+str(name), data)
        return JSONResponse('Metric has been added in the registy', status=201)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def metric_detail(request, name):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        metric = r.hgetall("metric:"+str(name))
        return JSONResponse(metric, status=200)

    if request.method == 'PUT':
        if not r.exists('metric:'+str(name)):
            return JSONResponse('Metric with name:  '+str(name)+' not exists.', status=404)

        data = JSONParser().parse(request)
        r.hmset('metric:'+str(name), data)
        return JSONResponse('The metadata of the metric workload with name: '+str(name)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("metric:"+str(id))
        return JSONResponse('Metric workload has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)


"""
Dynamic Filters part
"""
@csrf_exempt
def add_dynamic_filter(request):
    """
    Add a filter with its default parameters in the registry (redis)
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'GET':
        keys = r.keys("filter:*")
        dynamic_filters = []
        for key in keys:
            dynamic_filter = r.hgetall(key)
            dynamic_filter["name"]=key.split(":")[1]
            dynamic_filters.append(dynamic_filter)
        return JSONResponse(dynamic_filters, status=200)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Filter must have a name', status=400)
        r.hmset('filter:'+str(name), data)
        return JSONResponse('Filter has been added in the registy', status=201)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dynamic_filter_detail(request, name):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dynamic_filter = r.hgetall("filter:"+str(name))
        return JSONResponse(dynamic_filter, status=200)

    if request.method == 'PUT':
        if not r.exists('filter:'+str(name)):
            return JSONResponse('Dynamic filter with name:  '+str(name)+' not exists.', status=404)
        data = JSONParser().parse(request)
        r.hmset('filter:'+str(name), data)
        return JSONResponse('The metadata of the dynamic filter with name: '+str(name)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("filter:"+str(filter_id))
        return JSONResponse('Dynamic filter has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

"""
Tenants group part
"""
@csrf_exempt
def add_tenants_group(request):
    """
    Add a filter with its default parameters in the registry (redis)
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("G:*")
        gtenants = {}
        for key in keys:
            gtenant = r.lrange(key, 0, -1)
            gtenants[key] = gtenant
            #gtenants.extend(eval(gtenant[0]))
        return JSONResponse(gtenants, status=200)

    if request.method == 'POST':
        gtenant_id = r.incr("gtenant:id")
        data = JSONParser().parse(request)
        r.lpush('G:'+str(gtenant_id), *data)
        return JSONResponse('Tenants group has been added in the registy', status=201)

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def tenants_group_detail(request, gtenant_id):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        gtenant = r.lrange("G:"+str(gtenant_id), 0, -1)

        # r.hgetall("gtenants:"+str(gtenant_id))
        return JSONResponse(gtenant, status=200)

    if request.method == 'PUT':
        if not r.exists('G:'+str(gtenant_id)):
            return JSONResponse('The members of the tenants group with id:  '+str(gtenant_id)+' not exists.', status=404)
        data = JSONParser().parse(request)
        #for tenant in data:
        r.lpush('G:'+str(gtenant_id), *data)
        return JSONResponse('The members of the tenants group with id: '+str(gtenant_id)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("G:"+str(gtenant_id))
        return JSONResponse('Tenants grpup has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def gtenants_tenant_detail(request, gtenant_id, tenant_id):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'DELETE':
        r.lrem("G:"+str(gtenant_id), str(tenant_id), 1)
        return JSONResponse('Tenant'+str(tenant_id)+'has been deleted from group with the id: '+str(gtenant_id), status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)
