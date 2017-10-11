from django.conf import settings
from wsgiref.util import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView
import json
import logging
import mimetypes
import os

from api.common import to_json_bools, JSONResponse, get_redis_connection, \
    create_local_host, controller_actors, make_sure_path_exists, save_file, delete_file

logger = logging.getLogger(__name__)


#
# Controllers
#
@csrf_exempt
def controller_list(request):
    """
    List all global controllers.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys('controller:*')
        controller_list = []
        for key in keys:
            controller = r.hgetall(key)
            to_json_bools(controller, 'enabled')
            controller_list.append(controller)
        return JSONResponse(controller_list, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def controller_detail(request, controller_id):
    """
    Retrieve, update or delete a global controller.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        controller = r.hgetall('controller:' + str(controller_id))
        to_json_bools(controller, 'enabled')
        return JSONResponse(controller, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        print dir(request)
        data = json.loads(request.POST['metadata'])
        try:
            if request.FILES['file']:
                file_obj = request.FILES['file']
                make_sure_path_exists(settings.CONTROLLERS_DIR)
                path = save_file(file_obj, settings.CONTROLLERS_DIR)
                data['controller_name'] = os.path.basename(path)

            r.hmset('controller:' + str(controller_id), data)
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return JSONResponse("Error starting controller", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            controller = r.hgetall('controller:' + str(controller_id))
            delete_file(controller['controller_name'], settings.CONTROLLERS_DIR)
            r.delete("controller:" + str(controller_id))
        except:
            return JSONResponse("Error deleting controller", status=status.HTTP_400_BAD_REQUEST)

        # If this is the last controller, the counter is reset
        keys = r.keys('controller:*')
        if not keys:
            r.delete('controllers:id')

        return JSONResponse('Controller has been deleted', status=status.HTTP_204_NO_CONTENT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ControllerData(APIView):
    """
    Upload or download a global controller.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def post(self, request):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=500)

        data = json.loads(request.POST['metadata'])  # json data is in metadata parameter for this request
        if not data:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        controller_id = r.incr("controllers:id")

        try:
            data['id'] = controller_id
            file_obj = request.FILES['file']

            make_sure_path_exists(settings.CONTROLLERS_DIR)
            path = save_file(file_obj, settings.CONTROLLERS_DIR)
            data['controller_name'] = os.path.basename(path)

            r.hmset('controller:' + str(controller_id), data)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return JSONResponse("Error starting/stoping controller", status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return JSONResponse("Error uploading file", status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, controller_id):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('controller:' + str(controller_id)):
            global_controller_path = os.path.join(settings.CONTROLLERS_DIR,
                                                  str(r.hget('controller:' + str(controller_id), 'controller_name')))
            if os.path.exists(global_controller_path):
                global_controller_name = os.path.basename(global_controller_path)
                global_controller_size = os.stat(global_controller_path).st_size

                # Generate response
                response = StreamingHttpResponse(FileWrapper(open(global_controller_path), global_controller_size),
                                                 content_type=mimetypes.guess_type(global_controller_path)[0])
                response['Content-Length'] = global_controller_size
                response['Content-Disposition'] = "attachment; filename=%s" % global_controller_name

                return response
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)


#
# Instances
#
@csrf_exempt
def instences_list(request):
    """
    List all global controllers.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys('controller_instance:*')
        controller_list = []
        for key in keys:
            controller = r.hgetall(key)
            controller['id'] = key.split(':')[1]
            controller['controller'] = r.hgetall('controller:' + controller['controller'])['controller_name']
            controller_list.append(controller)
        return JSONResponse(controller_list, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def create_instance(request):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            r.hincrby('controller:' + data['controller'], 'instances', 1)
            r.hmset('controller_instance:' + str(r.incr('controller_instances:id')), data)
            return JSONResponse("Instance created", status=status.HTTP_201_CREATED)
        except Exception:
            return JSONResponse("Error creating instance", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def instance_detail(request, instance_id):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        try:
            controller = r.hgetall('controller_instance:' + str(instance_id))
            return JSONResponse(controller, status=status.HTTP_200_OK)
        except Exception:
            return JSONResponse("Error retrieving data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            if 'status' in data and data['status'] == 'Running':
                instance_data = r.hgetall('controller_instance:' + str(instance_id))
                controller_data = r.hgetall('controller:' + str(instance_data['controller']))
                controller_name = controller_data['controller_name'].split('.')[0]
                class_name = controller_data['class_name']
                parameters = instance_data['parameters']

                start_controller_instance(instance_id, controller_name, class_name, parameters)
            else:
                stop_controller_instance(instance_id)

            r.hmset('controller_instance:' + str(instance_id), data)
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            controller_id = 'controller:' + r.hgetall('controller_instance:' + instance_id)['controller']
            r.hincrby(controller_id, 'instances', -1)
            r.delete("controller_instance:" + str(instance_id))
        except:
            return JSONResponse("Error deleting controller", status=status.HTTP_400_BAD_REQUEST)

        # If this is the last controller, the counter is reset
        keys = r.keys('controller_instance:*')
        if not keys:
            r.delete('controller_instances:id')

        return JSONResponse('Instance has been deleted', status=status.HTTP_204_NO_CONTENT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


def start_controller_instance(instance_id, controller_name, controller_class_name, parameters):
    host = create_local_host()

    controller_location = os.path.join(controller_name, controller_class_name)
    parameters = parameters.strip().split(',')
    # params = {}
    params = list()
    for parameter in parameters:
        param_name, value = parameter.split('=')
        # params[param_name] = value
        params.append(value)

    try:
        if instance_id not in controller_actors:
            controller_actors[instance_id] = host.spawn(controller_name, controller_location, params)
            controller_actors[instance_id].run()
            logger.info("Controller, Started controller actor: "+controller_location)
    except Exception as e:
        logger.error(str(e.message))
        raise ValueError


def stop_controller_instance(instance_id):
    if instance_id in controller_actors:
        try:
            controller_actors[instance_id].stop_actor()
            del controller_actors[instance_id]
            logger.info("Controller, Stopped controller actor: " + str(instance_id))
        except Exception as e:
            logger.error(str(e))
            raise ValueError
