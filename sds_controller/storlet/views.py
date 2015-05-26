from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer

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
        serializer = SnippetSerializer(storlets, many=True)
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
    except storlet.DoesNotExist:
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
        except storlet.DoesNotExist:
            return HttpResponse(status=404)

        #TODO Update the path field

        return Response(status=201)
    if request.method == 'GET':
        #TODO Return the storlet data
        return Response(status=200)

def save_file(file, path=''):
    ''' Little helper to save a file
    '''
    filename = file._get_name()
    fd = open('%s/%s' % (MEDIA_ROOT, str(path) + str(filename)), 'wb')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) + str(filename)
