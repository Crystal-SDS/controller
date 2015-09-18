import requests
import ConfigParser
try:
    import simplejson as json
except ImportError:
    import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser

# Create your views here.

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

def proxyaddres():
    """
    Reads the proxy address from the Swift-proxy.conf file.
    """
    conf = ConfigParser.ConfigParser()
    conf.read('Swift-proxy.conf')
    proxyip = conf.get('proxy', 'proxyip')
    proxyport = conf.get('proxy', 'proxyport')
    proxy = "http://" + proxyip + ":" + proxyport
    return proxy

def is_valid_request(request):
    headers = {}
    try:
        headers['X-Auth-Token'] = request.META['HTTP_X_AUTH_TOKEN']
        return headers
    except:
        return None

@csrf_exempt
def bw_list(request):
    """
    Ask the proxy server information about the assigned BW to each
    account and policy.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'GET':
        address = proxyaddres() + "/bwdict/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP GET /bw/ requests allowed.', status=405)

@csrf_exempt
def bw_detail(request, account):
    """
    Ask the information of a certain tenant.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'GET':
        dict_json = dict()
        address = proxyaddres() + "/bwdict/"
        r = requests.get(address)
        data = json.loads(r.content)
        for os in data:
            dict_json[os] = { k : v for k,v in data[os].iteritems() if k == account}
        return JSONResponse(json.dumps(dict_json), content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP GET /bw/<account>/ requests allowed.', status=405)

@csrf_exempt
def bw_clear_all(request):
    """
    This call clears all the BW assignations for all accounts and policies.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'PUT':
        address = proxyaddres() + "/bwmod/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP PUT /bw/clear/ requests allowed.', status=405)

@csrf_exempt
def bw_clear_account(request, account):
    """
    This call clears all the BW assignations entries for the selected account.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'PUT':
        address = proxyaddres() + "/bwmod/" + account + "/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP PUT /bw/clear/<account>/ requests allowed.', status=405)

@csrf_exempt
def bw_clear_policy(request, account, policy):
    """
    This call clears all the BW assignations entries for the selected account
    and policy.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'PUT':
        address = proxyaddres() + "/bwmod/" + account + "/" + policy + "/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP PUT /bw/clear/<account>/<policy>/ requests allowed.', status=405)


@csrf_exempt
def bw_update(request, account, bw_value):
    '''
    This call assigns the specified bw to all the policies of the selected
    account
    '''
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'PUT':
        address = proxyaddres() + "/bwmod/" + account + "/" + bw_value + "/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP PUT /bw/<account>/<bw_value>/ requests allowed.', status=405)

@csrf_exempt
def bw_update_policy(request, account, policy, bw_value):
    '''
    This call assigns the specified bw to all the policies of the selected
    account
    '''
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'PUT':
        address = proxyaddres() + "/bwmod/" + account + "/" + policy + "/" + bw_value + "/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP PUT /bw/clear/<account>/<policy>/<bw_value>/ requests allowed.', status=405)


@csrf_exempt
def osinfo(request):
    """
    Ask the proxy server information about the current objects and its BW.
    """
    headers = is_valid_request(request)
    if not headers:
        return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
    if request.method == 'GET':
        address = proxyaddres() + "/osinfo/"
        r = requests.get(address)
        return HttpResponse(r.content, content_type = 'application/json', status=200)
    return JSONResponse('Only HTTP GET /bw/osinfo/ requests allowed.', status=405)
