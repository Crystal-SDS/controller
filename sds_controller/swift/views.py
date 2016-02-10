from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from django.conf import settings
import requests
from . import add_new_tenant
from . import deploy_image

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
    List swift tenants.
    """
    if request.method == 'GET':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        r = requests.get(settings.KEYSTONE_URL+"tenants", headers=headers)
        return HttpResponse(r.content, content_type = 'application/json', status=r.status_code)

    if request.method == "POST":
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        data = JSONParser().parse(request)
        try:
            add_new_tenant.add_new_tenant(data["tenant_name"], data["user_name"], data["user_password"])
        except:
            return JSONResponse('Error appear when creats an account.', status=500)
        try:
            deploy_image.deploy_image(data["tenant_name"], "ubuntu_14.04_jre8_storlets.tar", "192.168.2.1:5001/ubuntu_14.04_jre8_storlets" )
        except:
            return JSONResponse('Error appear when deploy storlet image.', status=500)
        return  JSONResponse('Account created successfully', status=201)
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
        try:
            create_storage_policies.create_storage_policy(data)
        except Exception, e:
            return JSONResponse('Error creating the Storage Policy', status=500)
        return  JSONResponse('Account created successfully', status=201)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)

@csrf_exempt
def locality_list(request, account, container=None, swift_object=None):
    """
    Shows the nodes where the account/container/object is stored. In the case that
    the account/container/object does not exist, return the nodes where it will be save.
    """
    if request.method == 'GET':
        if not container:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account)
        elif not swift_object:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account+"/"+container)
        elif container and swift_object:
            r = requests.get(settings.SWIFT_URL+"endpoints/v2/"+account+"/"+container+"/"+swift_object)
        return HttpResponse(r.content, content_type = 'application/json', status=r.status_code)
    return JSONResponse('Only HTTP GET /tenants/ requests allowed.', status=405)
