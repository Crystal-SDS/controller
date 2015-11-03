from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
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


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)

@csrf_exempt
def add_metric(request, name):
    """
    Add a metric workload in the registry (redis)
    """
    #TODO: Improve this method (update filter parameters?)
    if request.method == 'POST':
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Error connecting with DB', status=500)

        if not r.exists('metric:'+str(name)):
            data = JSONParser().parse(request)
            r.hmset('metric:'+str(name), data)
            return JSONResponse('Metric has been added in the registy', status=201)
        return JSONResponse('The filter '+str(name)+' already exists')

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def add_filter(request, name):
    """
    Add a filter with its default parameters in the registry (redis)
    """
    #TODO: Improve this method (update filter parameters?)
    if request.method == 'POST':
        try:
            r = get_redis_connection()
        except:
            return JSONResponse('Error connecting with DB', status=500)
        if not r.exists('filter:'+str(name)):
            data = JSONParser().parse(request)
            r.hmset('filter:'+str(name), data)
            return JSONResponse('Filter has been added in the registy', status=201)
        return JSONResponse('The filter '+str(name)+' already exists')

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)
