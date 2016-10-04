from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView
from operator import itemgetter
from pyactive.controller import init_host, start_controller
from redis.exceptions import RedisError, DataError

from api.exceptions import SwiftClientError, StorletNotFoundException, FileSynchronizationException
from api.common_utils import is_valid_request, rsync_dir_with_nodes, to_json_bools, remove_extra_whitespaces, JSONResponse, get_redis_connection, get_project_list
from filters.views import set_filter, unset_filter
from filters.views import save_file, make_sure_path_exists
import dsl_parser

import json
import mimetypes
import os
import re

host = None
remote_host = None
metrics = dict()
rules = dict()


def create_local_host():
    tcpconf = ('tcp', (settings.PYACTIVE_IP, settings.PYACTIVE_PORT))
    global host
    try:
        start_controller("pyactive_thread")
        host = init_host(tcpconf)
        print("Controller PyActive host created")
    except:
        pass


def load_metrics():
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    workload_metrics = r.keys("workload_metric:*")

    if workload_metrics:
        print "\nStarting workload metrics:"

    for wm in workload_metrics:
        wm_data = r.hgetall(wm)
        if wm_data['enabled'] == 'True':
            actor_id = wm_data['metric_name'].split('.')[0]
            metric_id = int(wm_data['id'])
            start_metric(metric_id, actor_id)


def load_policies():
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    dynamic_policies = r.keys("policy:*")

    if dynamic_policies:
        print "\nStarting dynamic rules stored in redis:"

    for policy in dynamic_policies:
        policy_data = r.hgetall(policy)

        if policy_data['alive'] == 'True':
            _, rule_parsed = dsl_parser.parse(policy_data['policy_description'])
            target = rule_parsed.target[0][1]  # Tenant ID or tenant+container
            for action_info in rule_parsed.action_list:
                if action_info.transient:
                    print 'Transient rule:', policy_data['policy_description']
                    rules[policy] = host.spawn_id(str(policy), settings.RULE_TRANSIENT_CLASS, settings.RULE_TRANSIENT_MAIN, 
                                                  [rule_parsed, action_info, target, host])
                    rules[policy].start_rule()
                else:
                    print 'Rule:', policy_data['policy_description']
                    rules[policy] = host.spawn_id(str(policy), settings.RULE_CLASS, settings.RULE_MAIN, 
                                                  [rule_parsed, action_info, target, host])
                    rules[policy].start_rule()


#
# Metric Workload part
#

@csrf_exempt
def add_metric(request):
    """
    Get all registered workload metrics (GET) or add a new metric workload in the registry (POST).

    :param request: The http request.
    :type request: HttpRequest
    :return: A JSON list with all registered metrics (GET) or a success/error message depending on the result of the function.
    :rtype: JSONResponse
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

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
    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Metric must have a name', status=400)
        r.hmset('metric:' + str(name), data)
        return JSONResponse('Metric has been added in the registry', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def metric_detail(request, name):
    """
    Get, update or delete a metric workload from the registry.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        metric = r.hgetall("metric:" + str(name))
        return JSONResponse(metric, status=200)

    if request.method == 'PUT':
        if not r.exists('metric:' + str(name)):
            return JSONResponse('Metric with name:  ' + str(name) + ' not exists.', status=404)

        data = JSONParser().parse(request)
        r.hmset('metric:' + str(name), data)
        return JSONResponse('The metadata of the metric workload with name: ' + str(name) + ' has been updated',
                            status=201)

    if request.method == 'DELETE':
        r.delete("metric:" + str(name))
        return JSONResponse('Metric workload has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Dynamic Filters part
#


@csrf_exempt
def add_dynamic_filter(request):
    """
    Add a filter with its default parameters in the registry (redis). 
    List all the dynamic filters registered.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'GET':
        keys = r.keys("dsl_filter:*")
        dynamic_filters = []
        for key in keys:
            dynamic_filter = r.hgetall(key)
            dynamic_filter["name"] = key.split(":")[1]
            dynamic_filters.append(dynamic_filter)
        return JSONResponse(dynamic_filters, status=200)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Filter must have a name', status=400)
        r.hmset('dsl_filter:' + str(name), data)
        return JSONResponse('Filter has been added in the registy', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dynamic_filter_detail(request, name):
    """
    Get, update or delete a dynamic filter from the registry.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        dynamic_filter = r.hgetall("dsl_filter:" + str(name))
        return JSONResponse(dynamic_filter, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        if not r.exists('dsl_filter:' + str(name)):
            return JSONResponse('Dynamic filter with name:  ' + str(name) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)
        data = JSONParser().parse(request)
        if 'name' in data:
            del data['name']
        r.hmset('dsl_filter:' + str(name), data)
        return JSONResponse('The metadata of the dynamic filter with name: ' + str(name) + ' has been updated',
                            status=status.HTTP_201_CREATED)

    if request.method == 'DELETE':
        filter_id = r.hget('dsl_filter:' + str(name), 'identifier')
        filter_name = r.hget('filter:' + str(filter_id), 'filter_name')

        keys = r.keys("pipeline:AUTH_*")
        for it in keys:
            for value in r.hgetall(it).values():
                json_value = json.loads(value)
                if json_value['filter_name'] == filter_name:
                    return JSONResponse('Unable to delete Registry DSL, is in use by some policy.', status=status.HTTP_403_FORBIDDEN)

        r.delete("dsl_filter:" + str(name))
        return JSONResponse('Dynamic filter has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Metric Modules
#
@csrf_exempt
def metric_module_list(request):
    """
    List all metric modules
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

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


def start_metric(metric_id, actor_id):
    create_local_host()
    print "- Metric, Starting workload metric actor " + str(metric_id)
    try:
        if metric_id not in metrics:
            metrics[metric_id] = host.spawn_id(actor_id, settings.METRIC_CLASS, settings.METRIC_MAIN, 
                                               ["amq.topic", actor_id, "metrics." + actor_id])
            metrics[metric_id].init_consum()
    except Exception as e:
        print e


def stop_metric(metric_id):
    if metric_id in metrics:
        print "- Metric, Stopping workload metric actor " + str(metric_id)
        metrics[metric_id].stop_actor()
        del metrics[metric_id]


@csrf_exempt
def metric_module_detail(request, metric_module_id):
    """
    Retrieve, update or delete a metric module.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

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

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if data['enabled']:
            if not 'metric_name' in data:
                wm_data = r.hgetall('workload_metric:' + str(metric_id))
                data['metric_name'] = wm_data['metric_name']

            actor_id = data['metric_name'].split('.')[0]
            start_metric(metric_id, actor_id)
        else:
            stop_metric(metric_id)

        try:
            r.hmset('workload_metric:' + str(metric_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            if metric_id in metrics:
                stop_metric(metric_id)

            r.delete("workload_metric:" + str(metric_id))
            keys = len(r.keys("workload_metric:*"))
            r.set('workload_metrics:id',keys)

            return JSONResponse('Workload metric has been deleted', status=status.HTTP_204_NO_CONTENT)
        except DataError:
            return JSONResponse("Error deleting workload metric", status=status.HTTP_408_REQUEST_TIMEOUT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class MetricModuleData(APIView):
    """
    Upload or download a metric module data.
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
                actor_id = data['metric_name'].split('.')[0]
                start_metric(workload_metric_id, actor_id)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print e
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


#
# Storage nodes
#

@csrf_exempt
def list_storage_node(request):
    """
    Add a storage node or list all the storage nodes saved in the registry.
    :param request:
    :return: JSONResponse
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == "GET":
        keys = r.keys("SN:*")
        storage_nodes = []
        for k in keys:
            sn = r.hgetall(k)
            sn["id"] = k.split(":")[1]
            storage_nodes.append(sn)
        sorted_list = sorted(storage_nodes, key=itemgetter('name'))
        return JSONResponse(sorted_list, status=200)

    if request.method == "POST":
        sn_id = r.incr("storage_nodes:id")
        data = JSONParser().parse(request)
        r.hmset('SN:' + str(sn_id), data)
        return JSONResponse('Storage node has been added to the registry', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def storage_node_detail(request, snode_id):
    """
    Get, update or delete a storage node from the registry.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        storage_node = r.hgetall("SN:" + str(snode_id))
        return JSONResponse(storage_node, status=200)

    if request.method == 'PUT':
        if not r.exists('SN:' + str(snode_id)):
            return JSONResponse('Storage node with name:  ' + str(snode_id) + ' not exists.', status=404)
        data = JSONParser().parse(request)
        r.hmset('SN:' + str(snode_id), data)
        return JSONResponse('The metadata of the storage node with name: ' + str(snode_id) + ' has been updated',
                            status=201)

    if request.method == 'DELETE':
        r.delete("SN:" + str(snode_id))
        return JSONResponse('Storage node has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Tenants group part
#
@csrf_exempt
def add_tenants_group(request):
    """
    Add a tenant group or list all the tenants groups saved in the registry.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("G:*")
        gtenants = {}
        for key in keys:
            gtenant = r.lrange(key, 0, -1)
            gtenant_id = key.split(":")[1]
            gtenants[gtenant_id] = gtenant
            # gtenants.extend(eval(gtenant[0]))
        return JSONResponse(gtenants, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        if not data:
            return JSONResponse('Tenant group cannot be empty',
                                status=status.HTTP_400_BAD_REQUEST)
        gtenant_id = r.incr("gtenant:id")
        r.rpush('G:' + str(gtenant_id), *data)
        return JSONResponse('Tenant group has been added to the registry', status=status.HTTP_201_CREATED)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def tenants_group_detail(request, gtenant_id):
    """
    Get, update or delete a tenants group from the registry.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        key = 'G:' + str(gtenant_id)
        if r.exists(key):
            gtenant = r.lrange(key, 0, -1)
            return JSONResponse(gtenant, status=status.HTTP_200_OK)
        else:
            return JSONResponse('The tenant group with id:  ' + str(gtenant_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        key = 'G:' + str(gtenant_id)
        if r.exists(key):
            data = JSONParser().parse(request)
            if not data:
                return JSONResponse('Tenant group cannot be empty',
                                    status=status.HTTP_400_BAD_REQUEST)
            pipe = r.pipeline()
            # the following commands are buffered in a single atomic request (to replace current contents)
            if pipe.delete(key).rpush(key, *data).execute():
                return JSONResponse('The members of the tenants group with id: ' + str(gtenant_id) + ' has been updated', status=status.HTTP_201_CREATED)
            return JSONResponse('Error storing the tenant group in the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return JSONResponse('The tenant group with id:  ' + str(gtenant_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        key = 'G:' + str(gtenant_id)
        if r.exists(key):
            r.delete("G:" + str(gtenant_id))
            return JSONResponse('Tenants grpup has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('The tenant group with id:  ' + str(gtenant_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def gtenants_tenant_detail(request, gtenant_id, tenant_id):
    """
    Delete a member from a tenants group.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'DELETE':
        r.lrem("G:" + str(gtenant_id), str(tenant_id), 1)
        return JSONResponse('Tenant ' + str(tenant_id) + ' has been deleted from group with the id: ' + str(gtenant_id),
                            status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Object Type part
#
@csrf_exempt
def object_type_list(request):
    """
    GET: List all object types.
    POST: Bind a new object type.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("object_type:*")
        object_types = []
        for key in keys:
            name = key.split(":")[1]
            types_list = r.lrange(key, 0, -1)
            object_types.append({"name": name, "types_list": types_list})
        return JSONResponse(object_types, status=status.HTTP_200_OK)

    if request.method == "POST":
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Object type must have a name as identifier', status=status.HTTP_400_BAD_REQUEST)
        if r.exists('object_type:' + str(name)):
            return JSONResponse('Object type ' + str(name) + ' already exists.', status=status.HTTP_400_BAD_REQUEST)
        if "types_list" not in data or not data["types_list"]:
            return JSONResponse('Object type must have a types_list defining the valid object types',
                                status=status.HTTP_400_BAD_REQUEST)

        if r.rpush('object_type:' + str(name), *data["types_list"]):
            return JSONResponse('Object type has been added in the registy', status=status.HTTP_201_CREATED)
        return JSONResponse('Error storing the object type in the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def object_type_detail(request, object_type_name):
    """
    GET: List extensions allowed about an object type word registered.
    PUT: Update the object type word registered.
    DELETE: Delete the object type word registered.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "object_type:" + object_type_name
    if request.method == 'GET':
        if r.exists(key):
            types_list = r.lrange(key, 0, -1)
            object_type = {"name": object_type_name, "types_list": types_list}
            return JSONResponse(object_type, status=status.HTTP_200_OK)
        return JSONResponse("Object type not found", status=status.HTTP_404_NOT_FOUND)

    if request.method == "PUT":
        if not r.exists(key):
            return JSONResponse('The object type with name: ' + object_type_name + ' does not exist.',
                                status=status.HTTP_404_NOT_FOUND)
        data = JSONParser().parse(request)
        if not data:
            return JSONResponse('Object type must have a types_list defining the valid object types',
                                status=status.HTTP_400_BAD_REQUEST)
        pipe = r.pipeline()
        # the following commands are buffered in a single atomic request (to replace current contents)
        if pipe.delete(key).rpush(key, *data).execute():
            return JSONResponse('The object type ' + str(object_type_name) + ' has been updated',
                                status=status.HTTP_201_CREATED)
        return JSONResponse('Error storing the object type in the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == "DELETE":
        if r.exists(key):
            object_type = r.delete(key)
            return JSONResponse(object_type, status=status.HTTP_200_OK)
        return JSONResponse("Object type not found", status=status.HTTP_404_NOT_FOUND)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def object_type_items_detail(request, object_type_name, item_name):
    """
    Delete an extension from an object type definition.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'DELETE':
        r.lrem("object_type:" + str(object_type_name), str(item_name), 1)
        return JSONResponse('Extension ' + str(item_name) + ' has been deleted from object type ' + str(object_type_name),
                            status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Node part
#

@csrf_exempt
def node_list(request):
    """
    GET: List all nodes ordered by name
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("node:*")
        nodes = []
        for key in keys:
            node = r.hgetall(key)
            node.pop("ssh_username", None)  # username & password are not returned in the list
            node.pop("ssh_password", None)
            node['devices'] = json.loads(node['devices'])
            nodes.append(node)
        sorted_list = sorted(nodes, key=itemgetter('name'))
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def node_detail(request, node_id):
    """
    GET: Retrieve node details. PUT: Update node.
    :param request:
    :param node_id:
    :return:
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    key = "node:" + node_id
    if request.method == 'GET':
        if r.exists(key):
            node = r.hgetall(key)
            node.pop("ssh_password", None)  # password is not returned
            node['devices'] = json.loads(node['devices'])
            return JSONResponse(node, status=status.HTTP_200_OK)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        if r.exists(key):
            data = JSONParser().parse(request)
            try:
                r.hmset(key, data)
                return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
            except RedisError:
                return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)
        else:
            return JSONResponse('Node not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def policy_list(request):
    """
    List all policies (sorted by execution_order). Deploy new policies.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)
 
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        if 'static' in str(request.path):
            project_list = get_project_list(token)
            keys = r.keys("pipeline:AUTH_*")
            policies = []
            for it in keys:
                for key, value in r.hgetall(it).items():
                    json_value = json.loads(value)
                    policies.append({'id': key, 'target_id': it.replace('pipeline:AUTH_', ''),
                                     'target_name': project_list[it.replace('pipeline:AUTH_', '').split(':')[0]],
                                     'filter_name': json_value['filter_name'], 'object_type': json_value['object_type'],
                                     'object_size': json_value['object_size'],
                                     'execution_server': json_value['execution_server'],
                                     'execution_server_reverse': json_value['execution_server_reverse'],
                                     'execution_order': json_value['execution_order'], 'params': json_value['params']})
            sorted_policies = sorted(policies, key=lambda x: int(itemgetter('execution_order')(x)))

            return JSONResponse(sorted_policies, status=status.HTTP_200_OK)

        elif 'dynamic' in str(request.path):
            keys = r.keys("policy:*")
            policies = []
            for key in keys:
                policy = r.hgetall(key)
                policies.append(policy)
            return JSONResponse(policies, status=status.HTTP_200_OK)

        else:
            return JSONResponse("Invalid request", status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':

        rules_string = request.body.splitlines()

        for rule_string in rules_string:
            #
            # Rules improved:
            # TODO: Handle the new parameters of the rule
            # Add containers and object in rules
            # Add execution server in rules
            # Add object type in rules
            #
            try:
                condition_list, rule_parsed = dsl_parser.parse(rule_string)

                if condition_list:
                    # Dynamic Rule
                    #print('Rule parsed:', rule_parsed)
                    deploy_policy(r, rule_string, rule_parsed)
                else:
                    # Static Rule
                    response = do_action(request, r, rule_parsed)
                    print("RESPONSE: " + str(response))

            except SwiftClientError:
                return JSONResponse('Error accessing Swift.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except StorletNotFoundException:
                return JSONResponse('Storlet not found.', status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                # print("The rule: " + rule_string + " cannot be parsed")
                # print("Exception message", e)
                return JSONResponse('Please, review the rule, register the dsl filter and start the workload '
                                    'metric before creating a new policy', status=status.HTTP_401_UNAUTHORIZED)

        return JSONResponse('Policies added successfully!', status=status.HTTP_201_CREATED)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def static_policy_detail(request, policy_id):
    """
    Retrieve, update or delete a static policy.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    target = str(policy_id).split(':')[:-1]
    target = ':'.join(target)
    policy = str(policy_id).split(':')[-1]

    if request.method == 'GET':
        project_list = get_project_list(token)
        policy_redis = r.hget("pipeline:AUTH_" + str(target), policy)
        data = json.loads(policy_redis)
        data["id"] = policy
        data["target_id"] = target
        data["target_name"] = project_list[target.split(':')[0]]
        return JSONResponse(data, status=200)
    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            policy_redis = r.hget("pipeline:AUTH_" + str(target), policy)
            json_data = json.loads(policy_redis)
            json_data.update(data)
            r.hset("pipeline:AUTH_" + str(target), policy, json.dumps(json_data))
            return JSONResponse("Data updated", status=201)
        except DataError:
            return JSONResponse("Error updating data", status=400)
    elif request.method == 'DELETE':
        r.hdel('pipeline:AUTH_' + target, policy)
        return JSONResponse('Policy has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def dynamic_policy_detail(request, policy_id):
    """
    Delete a dynamic policy.
    """
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'DELETE':
        create_local_host()

        try:
            rules[int(policy_id)].stop_actor()
            del rules[int(policy_id)]
        except Exception as e:
            print e

        r.delete('policy:' + policy_id)
        policies_ids = r.keys('policy:*')
        if len(policies_ids) == 0:
            r.set('policies:id',0)
        return JSONResponse('Policy has been deleted', status=204)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


def do_action(request, r, rule_parsed):
    # Validate request: only a user with admin role can access to this method
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

    for target in rule_parsed.target:
        for action_info in rule_parsed.action_list:
            print("TARGET RULE: ", action_info)
            dynamic_filter = r.hgetall("dsl_filter:" + str(action_info.filter))
            filter_data = r.hgetall("filter:" + dynamic_filter["identifier"])

            if not filter_data:
                return JSONResponse("Filter does not exist", status=status.HTTP_404_NOT_FOUND)

            if action_info.action == "SET":

                # Get an identifier of this new policy
                policy_id = r.incr("policies:id")

                # Set the policy data
                policy_data = {
                    "policy_id": policy_id,
                    "object_type": "",
                    "object_size": "",
                    "execution_order": policy_id,
                    "params": ""
                }

                # Rewrite default values
                if rule_parsed.object_list:
                    if rule_parsed.object_list.object_type:
                        policy_data["object_type"] = rule_parsed.object_list.object_type.object_value
                    if rule_parsed.object_list.object_size:
                        policy_data["object_size"] = [rule_parsed.object_list.object_size.operand,
                                                      rule_parsed.object_list.object_size.object_value]
                if action_info.execution_server:
                    policy_data["execution_server"] = action_info.execution_server
                if action_info.params:
                    policy_data["params"] = action_info.params

                # Deploy (an exception is raised if something goes wrong)
                set_filter(r, target[1], filter_data, policy_data, token)

            elif action_info.action == "DELETE":
                undeploy_response = unset_filter(r, target[1], filter_data, token)
                if undeploy_response != status.HTTP_204_NO_CONTENT:
                    return undeploy_response


def deploy_policy(r, rule_string, parsed_rule):
    create_local_host()
    rules_to_parse = dict()

    for target in parsed_rule.target:
        rules_to_parse[target[1]] = parsed_rule

    for key in rules_to_parse.keys():
        for action_info in rules_to_parse[key].action_list:
            policy_id = r.incr("policies:id")
            rule_id = 'policy:' + str(policy_id)

            if action_info.transient:
                #print 'Transient rule:', parsed_rule
                rules[policy_id] = host.spawn_id(rule_id, settings.RULE_TRANSIENT_CLASS, settings.RULE_TRANSIENT_MAIN,
                                                [rules_to_parse[key], action_info, key, host])
                location = os.path.join(settings.RULE_TRANSIENT_CLASS, settings.RULE_TRANSIENT_MAIN)
                is_transient = True
            else:
                #print 'Rule:', parsed_rule
                rules[policy_id] = host.spawn_id(rule_id, settings.RULE_CLASS, settings.RULE_MAIN,
                                                [rules_to_parse[key], action_info, key, host])
                location = os.path.join(settings.RULE_CLASS, settings.RULE_MAIN)
                is_transient = False

            rules[policy_id].start_rule()

            # FIXME Should we recreate a static rule for each target and action??
            condition_re = re.compile(r'.* (WHEN .*) DO .*', re.M|re.I)
            condition_str = condition_re.match(rule_string).group(1)

            tmp_rule_string = rule_string.replace(condition_str, '').replace('TRANSIENT', '')
            static_policy_rule_string = remove_extra_whitespaces(tmp_rule_string)

            # Add policy into redis
            policy_location = os.path.join(settings.PYACTIVE_URL, location, str(rule_id))
            r.hmset('policy:' + str(policy_id), {"id": policy_id, 
                                                 "policy": static_policy_rule_string,
                                                 "policy_description": rule_string,
                                                 "condition": condition_str.replace('WHEN ', ''),
                                                 "transient": is_transient,
                                                 "policy_location": policy_location,
                                                 "alive": True})
