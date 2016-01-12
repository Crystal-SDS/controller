from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from django.conf import settings
import requests

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

@csrf_exempt
def tenants_list(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        print request.META['HTTP_X_AUTH_TOKEN']
        r = requests.get(settings.KEYSTONE_URL+"tenants", headers=headers)
        return HttpResponse(r.content, content_type = 'application/json', status=r.status_code)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)

@csrf_exempt
def locality_list(request, account, container=None, swift_object=None):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        print account, container, swift_object
        if not container:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account)
        elif not swift_object:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account+"/"+container)
        elif container and swift_object:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account+"/"+container+"/"+swift_object)

        return HttpResponse(r.content, content_type = 'application/json', status=r.status_code)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)
