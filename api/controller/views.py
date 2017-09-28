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
from eventlet import sleep
import json
import logging
import mimetypes
import os

from api.common import to_json_bools, JSONResponse, get_redis_connection, \
    create_local_host, controller_actors, metric_actors

from filters.views import save_file, make_sure_path_exists

logger = logging.getLogger(__name__)


#
# Global Controllers
#
@csrf_exempt
def global_controller_list(request):
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
def global_controller_detail(request, controller_id):
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

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('controller:' + str(controller_id), data)
            controller_data = r.hgetall('controller:' + str(controller_id))
            to_json_bools(controller_data, 'enabled')

            if controller_data['enabled']:
                actor_id = controller_data['controller_name'].split('.')[0]
                start_global_controller(str(controller_id), actor_id, controller_data['class_name'], controller_data['type'], controller_data['dsl_filter'])
            else:
                stop_global_controller(str(controller_id))

            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        r.delete("controller:" + str(controller_id))

        # If this is the last controller, the counter is reset
        keys = r.keys('controller:*')
        if not keys:
            r.delete('controllers:id')

        return JSONResponse('Controller has been deleted', status=status.HTTP_204_NO_CONTENT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class GlobalControllerData(APIView):
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

            make_sure_path_exists(settings.GLOBAL_CONTROLLERS_DIR)
            path = save_file(file_obj, settings.GLOBAL_CONTROLLERS_DIR)
            data['controller_name'] = os.path.basename(path)

            r.hmset('controller:' + str(controller_id), data)

            if data['enabled']:
                actor_id = data['controller_name'].split('.')[0]
                start_global_controller(str(controller_id), actor_id, data['class_name'], data['type'], data['dsl_filter'])

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print e
            return JSONResponse("Error uploading file", status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, controller_id):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('controller:' + str(controller_id)):
            global_controller_path = os.path.join(settings.GLOBAL_CONTROLLERS_DIR,
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


def start_global_controller(controller_id, actor_id, controller_class_name, method_type, dsl_filter):

    host = create_local_host()
    logger.info("Controller, Starting controller actor " + str(controller_id) + " " + str(actor_id))

    # FIXME: Decouple global controllers and their related metrics
    try:
        if controller_id not in controller_actors:

            if dsl_filter == 'bandwidth':
                # 1) Spawn metric actor if not already spawned
                metric_name = method_type + "_bw_info"  # get_bw_info, put_bw_info, ssync_bw_info
                if metric_name not in metric_actors:
                    if method_type == 'ssync':
                        metric_module_name = 'controller.dynamic_policies.metrics.bw_info_ssync'
                        metric_class_name = 'BwInfoSSYNC'
                    else:
                        metric_module_name = 'controller.dynamic_policies.metrics.bw_info'
                        metric_class_name = 'BwInfo'
                    logger.info("Controller, Starting metric actor " + metric_name)
                    metric_actors[metric_name] = host.spawn(metric_name, metric_module_name + '/' + metric_class_name,
                                                            [metric_name, "bwdifferentiation."+metric_name+".#", method_type.upper()])

                    try:
                        metric_actors[metric_name].init_consum()
                        logger.info("Controller, Started metric actor " + metric_name)
                        sleep(0.1)
                    except Exception as e:
                        logger.error(e.args)
                        logger.info("Controller, Failed to start metric actor " + metric_name)
                        metric_actors[metric_name].stop_actor()
            else:
                # FIXME: Obtain the related metric_name that the global controller must observe
                metric_name = 'dummy'

            # 2) Spawn controller actor
            # module_name = ''.join([settings.GLOBAL_CONTROLLERS_BASE_MODULE, '.', actor_id])
            module_name = actor_id
            controller_actors[controller_id] = host.spawn(actor_id, module_name + '/' + controller_class_name,
                                                          ["bw_algorithm_" + method_type, method_type.upper()])
            logger.info("Controller, Started controller actor " + str(controller_id) + " " + str(actor_id))
            # ["abstract_enforcement_algorithm_get", "GET"])
            # ["amq.topic", actor_id, "controllers." + actor_id])

            controller_actors[controller_id].run(metric_name)
    except Exception as e:
        print e


def stop_global_controller(controller_id):
    if controller_id in controller_actors:
        try:
            controller_actors[controller_id].stop_actor()
        except Exception as e:
            print e.args
        del controller_actors[controller_id]
        logger.info("Controller, Stopped controller actor " + str(controller_id))
