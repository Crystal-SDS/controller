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
from operator import itemgetter
import json
import logging
import mimetypes
import os

from api.common import to_json_bools, JSONResponse, get_redis_connection, \
    rsync_dir_with_nodes, create_local_host, metric_actors, make_sure_path_exists, save_file

from api.exceptions import FileSynchronizationException


logger = logging.getLogger(__name__)


def load_metrics():
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    workload_metrics = r.keys("workload_metric:*")

    if workload_metrics:
        logger.info("Starting workload metrics")

    for wm in workload_metrics:
        wm_data = r.hgetall(wm)
        if wm_data['enabled'] == 'True':
            actor_id = wm_data['metric_name'].split('.')[0]
            metric_id = int(wm_data['id'])
            start_metric(metric_id, actor_id)


@csrf_exempt
def list_activated_metrics(request):
    """
    Get all registered workload metrics (GET) or add a new metric workload in the registry (POST).

    :param request: The http request.
    :type request: HttpRequest
    :return: A JSON list with all registered metrics (GET) or a success/error message depending on the result of the function.
    :rtype: JSONResponse
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("metric:*")
        metrics = []
        for key in keys:
            metric = r.hgetall(key)
            metric["name"] = key.split(":")[1]
            metrics.append(metric)
        return JSONResponse(metrics, status=200)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Metric Modules
#
@csrf_exempt
def metric_module_list(request):
    """
    List all metric modules
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'GET':
        keys = r.keys("workload_metric:*")
        workload_metrics = []
        for key in keys:
            metric = r.hgetall(key)
            to_json_bools(metric, 'in_flow', 'out_flow', 'enabled')
            workload_metrics.append(metric)
        sorted_workload_metrics = sorted(workload_metrics, key=lambda x: int(itemgetter('id')(x)))
        return JSONResponse(sorted_workload_metrics, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


def start_metric(actor_id):
    host = create_local_host()
    logger.info("Metric, Starting workload metric actor: " + str(actor_id))
    try:
        if actor_id not in metric_actors:
            metric_actors[actor_id] = host.spawn(actor_id, settings.METRIC_MODULE,
                                                 [actor_id, "metric." + actor_id])
            metric_actors[actor_id].init_consum()
    except Exception:
        logger.error("Metric, Error starting workload metric actor: " + str(actor_id))
        raise Exception


def stop_metric(actor_id):
    if actor_id in metric_actors:
        logger.info("Metric, Stopping workload metric actor: " + str(actor_id))
        metric_actors[actor_id].stop_actor()
        del metric_actors[actor_id]


@csrf_exempt
def metric_module_detail(request, metric_module_id):
    """
    Retrieve, update or delete a metric module.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    metric_id = int(metric_module_id)
    if not r.exists("workload_metric:" + str(metric_id)):
        return JSONResponse('Object does not exist!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        metric = r.hgetall("workload_metric:" + str(metric_id))

        to_json_bools(metric, 'in_flow', 'out_flow', 'enabled')
        return JSONResponse(metric, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if len(data) == 1:
            # Enable/disable button
            redis_data = r.hgetall('workload_metric:' + str(metric_id))
            redis_data.update(data)
            data = redis_data

        if 'metric_name' not in data:
            metric_name = r.hget('workload_metric:' + str(metric_id), 'metric_name').split('.')[0]
        else:
            metric_name = data['metric_name'].split('.')[0]

        if data['enabled']:
            try:
                if data['in_flow'] == 'True':
                    start_metric('put_'+metric_name)
                if data['out_flow'] == 'True':
                    start_metric('get_'+metric_name)
            except Exception:
                data['enabled'] = False
        else:
            if data['in_flow'] == 'True':
                stop_metric('put_'+metric_name)
            if data['out_flow'] == 'True':
                stop_metric('get_'+metric_name)

        try:
            r.hmset('workload_metric:' + str(metric_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            wm_data = r.hgetall('workload_metric:' + str(metric_id))
            metric_name = wm_data['metric_name'].split('.')[0]

            if wm_data['in_flow'] == 'True':
                actor_id = 'put_'+metric_name
                if actor_id in metric_actors:
                    stop_metric(actor_id)
            if wm_data['out_flow'] == 'True':
                actor_id = 'get_'+metric_name
                if actor_id in metric_actors:
                    stop_metric(actor_id)

            r.delete('workload_metric:' + str(metric_id))

            wm_ids = r.keys('workload_metric:*')
            if len(wm_ids) == 0:
                r.set('workload_metrics:id', 0)

            return JSONResponse('Workload metric has been deleted', status=status.HTTP_204_NO_CONTENT)
        except DataError:
            return JSONResponse("Error deleting workload metric", status=status.HTTP_408_REQUEST_TIMEOUT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class MetricModuleData(APIView):
    """
    Upload or download a metric module data.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=500)

        data = json.loads(request.POST['metadata'])  # json data is in metadata parameter for this request
        if not data:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        workload_metric_id = r.incr("workload_metrics:id")
        try:
            data['id'] = workload_metric_id

            file_obj = request.FILES['file']

            make_sure_path_exists(settings.WORKLOAD_METRICS_DIR)
            path = save_file(file_obj, settings.WORKLOAD_METRICS_DIR)
            data['metric_name'] = os.path.basename(path)

            # synchronize metrics directory with all nodes
            try:
                rsync_dir_with_nodes(settings.WORKLOAD_METRICS_DIR)
            except FileSynchronizationException as e:
                # print "FileSynchronizationException", e  # TODO remove
                return JSONResponse(e.message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            r.hmset('workload_metric:' + str(workload_metric_id), data)

            if data['enabled']:
                metric_name = data['metric_name'].split('.')[0]
                if data['in_flow']:
                    start_metric('put_'+metric_name)
                if data['out_flow']:
                    start_metric('get_'+metric_name)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print e
            logger.error(str(e))
            return JSONResponse("Error uploading file", status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, metric_module_id):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('workload_metric:' + str(metric_module_id)):
            workload_metric_path = os.path.join(settings.WORKLOAD_METRICS_DIR,
                                                str(r.hget('workload_metric:' + str(metric_module_id), 'metric_name')))
            if os.path.exists(workload_metric_path):
                workload_metric_name = os.path.basename(workload_metric_path)
                workload_metric_size = os.stat(workload_metric_path).st_size

                # Generate response
                response = StreamingHttpResponse(FileWrapper(open(workload_metric_path), workload_metric_size),
                                                 content_type=mimetypes.guess_type(workload_metric_path)[0])
                response['Content-Length'] = workload_metric_size
                response['Content-Disposition'] = "attachment; filename=%s" % workload_metric_name

                return response
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
