import json
import mimetypes
import os
import re
from operator import itemgetter

import redis
import requests
from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from pyactive.controller import init_host, start_controller
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

import dsl_parser
from sds_controller.exceptions import SwiftClientError, StorletNotFoundException, FileSynchronizationException
from sds_controller.common_utils import rsync_dir_with_nodes, to_json_bools, remove_extra_whitespaces

from storlet.views import deploy, undeploy
from storlet.views import save_file, make_sure_path_exists

host = None
remote_host = None


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
    except KeyError:
        return None


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


# TODO: Improve the implementation to create the host connection
def create_host():
    print("  --- CREATING HOST ---")
    start_controller("pyactive_thread")
    tcpconf = ('tcp', ('127.0.0.1', 9899))
    # momconf = ('mom',{'name':'api_host','ip':'127.0.0.1','port':61613, 'namespace':'/topic/iostack'})
    global host
    host = init_host(tcpconf)
    global remote_host
    print("  **  ")
    remote_host = host.lookup_remote_host(settings.PYACTIVE_URL + 'controller/Host/0')
    remote_host.hello()
    print('lookup', remote_host)


#
# Metric Workload part
#


@csrf_exempt
def add_metric(request):
    """
    Add a metric workload in the registry (redis)
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
    Add a filter with its default parameters in the registry (redis). List all the dynamic filters registered.
    """
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
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dynamic_filter = r.hgetall("dsl_filter:" + str(name))
        return JSONResponse(dynamic_filter, status=200)

    if request.method == 'PUT':
        if not r.exists('dsl_filter:' + str(name)):
            return JSONResponse('Dynamic filter with name:  ' + str(name) + ' not exists.', status=404)
        data = JSONParser().parse(request)
        if 'name' in data:
            del data['name']
        r.hmset('dsl_filter:' + str(name), data)
        return JSONResponse('The metadata of the dynamic filter with name: ' + str(name) + ' has been updated',
                            status=201)

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
        return JSONResponse('Dynamic filter has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Metric Modules
#
@csrf_exempt
def metric_module_list(request):
    """
    List all metric modules, or create a new metric module.
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


@csrf_exempt
def metric_module_detail(request, metric_module_id):
    """
    Retrieve, update or delete a metric module.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not r.exists("workload_metric:" + str(metric_module_id)):
        return JSONResponse('Object does not exist!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        metric = r.hgetall("workload_metric:" + str(metric_module_id))

        to_json_bools(metric, 'in_flow', 'out_flow', 'enabled')
        return JSONResponse(metric, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        try:
            r.hmset('workload_metric:' + str(metric_module_id), data)
            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            r.delete("workload_metric:" + str(metric_module_id))
            return JSONResponse('Workload metric has been deleted', status=status.HTTP_204_NO_CONTENT)
        except DataError:
            return JSONResponse("Error deleting workload metric", status=status.HTTP_408_REQUEST_TIMEOUT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class MetricModuleData(APIView):
    """
    Upload or get a metric module data.
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
            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
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
                response = StreamingHttpResponse(FileWrapper(open(workload_metric_path), workload_metric_size), content_type=mimetypes.guess_type(workload_metric_path)[0])
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
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        if 'static' in str(request.path):
            headers = is_valid_request(request)
            if not headers:
                return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
            keystone_response = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)
            keystone_tenants = json.loads(keystone_response.content)['tenants']

            tenants_list = {}
            for tenant in keystone_tenants:
                tenants_list[tenant["id"]] = tenant["name"]

            keys = r.keys("pipeline:AUTH_*")
            policies = []
            for it in keys:
                for key, value in r.hgetall(it).items():
                    json_value = json.loads(value)
                    policies.append({'id': key, 'target_id': it.replace('pipeline:AUTH_', ''),
                                     'target_name': tenants_list[it.replace('pipeline:AUTH_', '').split(':')[0]],
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
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=status.HTTP_401_UNAUTHORIZED)
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
                    print('Rule parsed:', rule_parsed)
                    deploy_policy(r, rule_string, rule_parsed)
                else:
                    # Static Rule
                    response = do_action(request, r, rule_parsed, headers)
                    print("RESPONSE: " + str(response))

            except SwiftClientError:
                return JSONResponse('Error accessing Swift.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except StorletNotFoundException:
                return JSONResponse('Storlet not found.', status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                # print("The rule: " + rule_string + " cannot be parsed")
                # print("Exception message", e)
                return JSONResponse("Error in rule: " + rule_string + " Error message --> " + str(e),
                                    status=status.HTTP_401_UNAUTHORIZED)

        return JSONResponse('Policies added successfully!', status=status.HTTP_201_CREATED)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def static_policy_detail(request, policy_id):
    """
    Retrieve, update or delete SLA.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    target = str(policy_id).split(':')[:-1]
    target = ':'.join(target)
    policy = str(policy_id).split(':')[-1]

    if request.method == 'GET':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse(
                'You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        keystone_response = requests.get(settings.KEYSTONE_URL + "tenants", headers=headers)
        keystone_tenants = json.loads(keystone_response.content)["tenants"]

        tenants_list = {}
        for tenant in keystone_tenants:
            tenants_list[tenant["id"]] = tenant["name"]

        policy_redis = r.hget("pipeline:AUTH_" + str(target), policy)
        data = json.loads(policy_redis)
        data["id"] = policy
        data["target_id"] = target
        data["target_name"] = tenants_list[target.split(':')[0]]
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
    Retrieve, update or delete SLA.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'DELETE':
        # TODO: Kill actor when deletes a redis key
        r.delete('policy:' + policy_id)
        return JSONResponse('Policy has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


def do_action(request, r, rule_parsed, headers):
    for target in rule_parsed.target:
        for action_info in rule_parsed.action_list:
            print("TARGET RULE: ", action_info)
            dynamic_filter = r.hgetall("dsl_filter:" + str(action_info.filter))
            storlet = r.hgetall("filter:" + dynamic_filter["identifier"])

            if not storlet:
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
                deploy(r, target[1], storlet, policy_data, headers)

            elif action_info.action == "DELETE":
                undeploy_response = undeploy(r, target[1], storlet, headers)
                if undeploy_response != status.HTTP_204_NO_CONTENT:
                    return undeploy_response


def deploy_policy(r, rule_string, parsed_rule):
    # self.aref = 'atom://' + self.dispatcher.name + '/controller/Host/0'
    rules = {}
    cont = 0

    if not host or not remote_host:
        create_host()

    rules_to_parse = {}

    for target in parsed_rule.target:
        rules_to_parse[target[1]] = parsed_rule

    for key in rules_to_parse.keys():
        for action_info in rules_to_parse[key].action_list:
            policy_id = r.incr("policies:id")

            if action_info.transient:
                print 'Transient rule:', parsed_rule
                rules[cont] = remote_host.spawn_id('policy:' + str(policy_id), 'rule_transient', 'TransientRule',
                                                    [rules_to_parse[key], action_info, key, remote_host])
                location = "rule_transient/TransientRule/"
                is_transient = True
            else:
                print 'Rule:', parsed_rule
                rules[cont] = remote_host.spawn_id('policy:' + str(policy_id), 'rule', 'Rule',
                                                   [rules_to_parse[key], action_info, key, remote_host])
                location = "rule/Rule/"
                is_transient = False

            rules[cont].start_rule()

            # FIXME Should we recreate a static rule for each target and action??
            condition_re = re.compile(r'.* (WHEN .*) DO .*', re.M|re.I)
            condition_str = condition_re.match(rule_string).group(1)

            tmp_rule_string = rule_string.replace(condition_str, '').replace('TRANSIENT', '')
            static_policy_rule_string = remove_extra_whitespaces(tmp_rule_string)

            # Add policy into redis
            r.hmset('policy:' + str(policy_id),
                    {"id": policy_id, "policy": static_policy_rule_string, "policy_description": parsed_rule,
                     "condition": condition_str.replace('WHEN ', ''), "transient": is_transient,
                     "policy_location": settings.PYACTIVE_URL + location + str(policy_id), "alive": True})
            cont += 1
