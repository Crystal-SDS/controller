from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from storlet.models import Storlet, Dependency
from storlet.serializers import StorletSerializer, DependencySerializer

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
def storlet_list(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        storlets = Storlet.objects.all()
        serializer = StorletSerializer(storlets, many=True)
        return JSONResponse(serializer.data)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = StorletSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

@csrf_exempt
def storlet_detail(request, id):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = StorletSerializer(storlet)
        return JSONResponse(serializer.data)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = StorletSerializer(storlet, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        storlet.delete()
        return HttpResponse(status=204)

@csrf_exempt
def storlet_data(request, id):
    parser_classes = (FileUploadParser,)

    if request.method == 'PUT':
        file_obj = request.FILES['file']
        path = save_file(file_obj, './sotrlets_jar/')
        try:
            storlet = Storlet.objects.get(id=id)
            storlet.path = path
        except Storlet.DoesNotExist:
            return HttpResponse(status=404)

        #TODO Update the path field

        return Response(status=201)
    if request.method == 'GET':
        #TODO Return the storlet data
        return Response(status=200)


@csrf_exempt
def storlet_deploy(request, id):
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'PUT':
        #TODO Call swift using storlets parameters to deploy it
        return Response(status=201)


@csrf_exempt
def dependency_list(request):
    """
    List all code snippets, or create a Dependency.
    """
    if request.method == 'GET':
        dependencies = Dependency.objects.all()
        serializer = DependencySerializer(dependencies, many=True)
        return JSONResponse(serializer.data)

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
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = DependencySerializer(dependency)
        return JSONResponse(serializer.data)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = DependencySerializer(dependency, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        dependency.delete()
        return HttpResponse(status=204)

@csrf_exempt
def dependency_data(request, name):
    parser_classes = (FileUploadParser,)

    if request.method == 'PUT':
        file_obj = request.FILES['file']
        path = save_file(file_obj, './dependencies/')
        try:
            dependency = Dependency.objects.get(name=name)
            dependency.path = path
        except Dependency.DoesNotExist:
            return HttpResponse(status=404)

        #TODO Update the path field

        return Response(status=201)
    if request.method == 'GET':
        #TODO Return the storlet data
        return Response(status=200)

@csrf_exempt
def dependency_deploy(request, name):
    try:
        dependency = Dependency.objects.get(name=name)
    except Dependency.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'PUT':
        #TODO Call swift using storlets parameters to deploy it
        return Response(status=201)


def save_file(file, path=''):
    '''
    Little helper to save a file
    '''
    filename = file._get_name()
    fd = open('%s/%s' % (MEDIA_ROOT, str(path) + str(filename)), 'wb')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) + str(filename)
