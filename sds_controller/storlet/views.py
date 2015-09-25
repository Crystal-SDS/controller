from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser, FormParser
from storlet.models import Storlet, Dependency, StorletUser
from storlet.serializers import StorletSerializer, DependencySerializer, StorletUserSerializer
from swiftclient import client as c
from rest_framework.views import APIView
from django.conf import settings
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

class StorletList(APIView):
    """
    List all storlets, or create a new storlet.
    """
    def get(self, request, format=None):
        storlets = Storlet.objects.all()
        serializer = StorletSerializer(storlets, many=True)
        return JSONResponse(serializer.data)

    def post(self, request, format=None):
        data = JSONParser().parse(request)
        serializer = StorletSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

@csrf_exempt
def storlet_detail(request, id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'GET':
        serializer = StorletSerializer(storlet)
        return JSONResponse(serializer.data, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = StorletSerializer(storlet, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        storlet.delete()
        return JSONResponse('Storlet has been deleted', status=204)

class StorletData(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    def put(self, request, id, format=None):
        file_obj = request.FILES['file']
        path = save_file(file_obj, settings.STORLET_DIR)
        try:
            storlet = Storlet.objects.get(id=id)
            storlet.path = path
            storlet.save()
        except Storlet.DoesNotExist:
            return JSONResponse('Storlet does not exists', status=404)
        return JSONResponse('Storlet has been updated', status=201)
    def get(self, request, id, format=None):
        #TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)

@csrf_exempt
def storlet_deploy(request, id, account):
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return JSONResponse('Storlet does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        #TODO: add params in the request body
        data = JSONParser().parse(request)

        metadata = {'X-Object-Meta-Storlet-Language':'Java',
            'X-Object-Meta-Storlet-Interface-Version':'1.0',
            'X-Object-Meta-Storlet-Dependency': storlet.dependency,
            'X-Object-Meta-Storlet-Object-Metadata':'no',
            'X-Object-Meta-Storlet-Main': storlet.main_class}
        f = open(storlet.path,'r')
        content_length = None
        response = dict()
        #Change to API Call
        c.put_object(settings.SWIFT_URL+"AUTH_"+str(account), headers["X-Auth-Token"], 'storlet', storlet.name, f,
                     content_length, None, None,
                     "application/octet-stream", metadata,
                     None, None, None, response)
        f.close()
        status = response.get('status')
        if status == 201:
            try:
                storlet_user = StorletUser.objects.get(storlet=storlet, user_id=account)
                return JSONResponse("Already deployed", status=200)
            except StorletUser.DoesNotExist:
                storlet_user = StorletUser.objects.create(storlet_id=storlet.id, user_id=account, parameters=data["params"])
                return JSONResponse("Deployed", status=201)

        return JSONResponse("error", status=400)

@csrf_exempt
def storlet_list_deployed(request, account):

    if request.method == 'GET':
        try:
            storlets = StorletUser.objects.filter(user_id=account)
        except StorletUser.DoesNotExist:
	           return JSONResponse('Any Storlet deployed', status=404)
        serializer = StorletUserSerializer(storlets, many=True)
        return JSONResponse(serializer.data, status=200)

@csrf_exempt
def storlet_undeploy(request, id, account):
    try:
        storlet_user = StorletUser.objects.get(storlet_id=id, user_id=account,)
    except Storlet.DoesNotExist:
        return JSONResponse('Storlet does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        c.delete_object(settings.SWIFT_URL+"AUTH_"+str(account),headers["X-Auth-Token"],
            'storlet', storlet_user.storlet.name, None, None, None, None, response)

        status = response.get('status')
        if status == 200:
            deleted = StorletUser.objects.delete(id=storlet_user.id)
            return JSONResponse("The object has been deleted", status=status)
        return JSONResponse(response.get["reason"], status=status)

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
    if request.method == 'GET':
        dependencies = Dependency.objects.all()
        serializer = DependencySerializer(dependencies, many=True)
        return JSONResponse(serializer.data, status=202)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = DependencySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

@csrf_exempt
def dependency_detail(request, name):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        dependency = Dependency.objects.get(name=name)
    except Dependency.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'GET':
        serializer = DependencySerializer(dependency)
        return JSONResponse(serializer.data, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = DependencySerializer(dependency, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        dependency.delete()
        return JSONResponse('Dependency with id:'+str(id)+'has been deleted', status=204)

@csrf_exempt
def dependency_data(request, name):

    if request.method == 'PUT':
        file_obj = request.FILES['file']
        path = save_file(file_obj, settings.DEPENDENCY_DIR)
        try:
            dependency = Dependency.objects.get(name=name)
            dependency.path = path
            dependency.save()
        except Dependency.DoesNotExist:
            return JSONResponse('Dependency does not exists', status=404)

        #TODO Update the path field
        serializer = DependencySerializer(dependency)
        return JSONResponse(serializer.data, status=201)
    if request.method == 'GET':
        #TODO Return the dependency data
        return JSONResponse('return data', status=200)

@csrf_exempt
def dependency_deploy(request, name, account):
    try:
        dependency = Dependency.objects.get(name=name)
    except Dependency.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        data = JSONParser().parse(request)

        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency.version)}
        f = open(dependency.path,'r')
        content_length = None
        response = dict()
        c.put_object(settings.SWIFT_URL+"AUTH_"+str(account), headers["X-Auth-Token"], 'dependency', dependency.name, f,
                     content_length, None, None, "application/octet-stream",
                     metadata, None, None, None, response)
        f.close()
        status = response.get('status')
        if 200 <= status < 300:
            try:
                #TODO: Control version, it's possible add call to updrade the version
                storlet_user = DependencyUser.objects.get(dependency=dependency, user_id=account)
                return JSONResponse("Already deployed", status=200)
            except StorletUser.DoesNotExist:
                storlet_user = StorletUser.objects.create(dependency_id=dependency.id, user_id=account)
                return JSONResponse("Deployed", status=201)
        return JSONResponse('ERROR',status=500)

@csrf_exempt
def dependency_list_deployed(request, account):

    if request.method == 'GET':
        try:
            dependency = DependencyUser.objects.filter(user_id=account)
        except StorletUser.DoesNotExist:
	           return JSONResponse('Any Dependency deployed', status=404)
        serializer = StorletUserSerializer(dependency, many=True)
        return JSONResponse(serializer.data, status=200)

@csrf_exempt
def dependency_undeploy(request, name, account):
    try:
        dependency = Dependency.objects.get(name=name)
        dependency_user = DependencyUser.objects.get(storlet_id=dependency.id, user_id=account)
    except Storlet.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        c.delete_object(settings.SWIFT_URL+"AUTH_"+str(account),headers["X-Auth-Token"],
            'dependency', dependency.name, None, None, None, None, response)

        status = response.get('status')
        if status == 200:
            deleted = StorletUser.objects.delete(id=dependency_user.id)
            return JSONResponse("The object has been deleted", status=status)
        return JSONResponse(response.get["reason"], status=status)

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
