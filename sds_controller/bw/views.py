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

@csrf_exempt
def bw_list(request):
    """
    Ask the proxy server information about the assigned BW to each
    account and policy.
    """
    if request.method == 'GET':
        #TODO Call swift to obtain the data
        #example
        '''
        data = call_to_swift("proxyhost:proxyhost/bwdict/")
        return data
        '''
        return None

@csrf_exempt
def bw_detail(request, account):
    """
    Ask the information of a certain tenant.
    """
    if request.method == 'GET':
        #TODO Call swift to obtain the data
        #example
        '''
        data = call_to_swift("proxyhost:proxyhost/bwdict/<account>")
        return data
        '''
        return None
    return None

@csrf_exempt
def bw_clear_all(request):
    """
    This call clears all the BW assignations for all accounts and policies.
    """
    if request.method == 'PUT':
        #TODO Call swift to obtain the data
        #example
        '''
        data = call_to_swift("<proxyip>:<proxyport>/bwmod/")
        return data
        '''
        return None

@csrf_exempt
def bw_clear_account(request, account):
    """
    This call clears all the BW assignations entries for the selected account.
    """
    if request.method == 'PUT':
        #TODO Call swift to obtain the data
        #example
        '''
        data = call_to_swift("<proxyip>:<proxyport>/bwmod/<account>")
        return data
        '''
        return None

@csrf_exempt
def bw_clear_policy(request, account, policy):
    """
    This call clears all the BW assignations entries for the selected account
    and policy.
    """
    if request.method == 'PUT':
        #TODO Call swift to obtain the data
        #example
        '''
        data = call_to_swift("<proxyip>:<proxyport>/bwmod/<account>/<policy>")
        return data
        '''
        return None

@csrf_exempt
def bw_update(request, account, bw_value):
    '''
    This call assigns the specified bw to all the policies of the selected
    account
    '''
    if request.method == 'PUT':
        #TODO Call swift to obtain the data
        #example
        '''
        try:
            response = call_to_swift("<proxyip>:<proxyport>/bwmod/<account>/<bw_value>")
        except storlet.DoesNotExist:
            return HttpResponse(status=404)
        return Response(status=200)
        '''
        return None
@csrf_exempt
def bw_update_policy(request, account, policy, bw_value):
    '''
    This call assigns the specified bw to all the policies of the selected
    account
    '''
    if request.method == 'PUT':
        #TODO Call swift to obtain the data
        #example
        '''
        try:
            response = call_to_swift("<proxyip>:<proxyport>/bwmod/<account>/<policy>/bw_value")
        except storlet.DoesNotExist:
            return HttpResponse(status=404)
        return Response(status=200)
        '''
        return None
