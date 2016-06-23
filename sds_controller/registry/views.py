import json

import redis
import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from pyactive.controller import init_host, start_controller
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from storlet.views import deploy, undeploy
from sds_controller.exceptions import SwiftClientError, StorletNotFoundException

import dsl_parser

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
    except:
        return None


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


# TODO: Improve the implementation to create the host connection
def create_host():
    print "  --- CREATING HOST ---"
    start_controller("pyactive_thread")
    tcpconf = ('tcp', ('127.0.0.1', 9899))
    # momconf = ('mom',{'name':'api_host','ip':'127.0.0.1','port':61613, 'namespace':'/topic/iostack'})
    global host
    host = init_host(tcpconf)
    global remote_host
    print "  **  "
    remote_host = host.lookup_remote_host(settings.PYACTIVE_URL + 'controller/Host/0')
    remote_host.hello()
    print 'lookup', remote_host


"""
Metric Workload part
"""


@csrf_exempt
def add_metric(request):
    """
    Add a metric workload in the registry (redis)
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("metric:*")
        print 'keys', keys
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
        return JSONResponse('Metric has been added in the registy', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def metric_detail(request, name):
    """
    Get, update or delete a metric workload from the registry.
    """
    try:
        r = get_redis_connection()
    except:
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
        r.delete("metric:" + str(id))
        return JSONResponse('Metric workload has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


"""
Dynamic Filters part
"""


@csrf_exempt
def add_dynamic_filter(request):
    """
    Add a filter with its default parameters in the registry (redis). List all the dynamic filters registered.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'GET':
        keys = r.keys("filter:*")
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
        r.hmset('filter:' + str(name), data)
        return JSONResponse('Filter has been added in the registy', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dynamic_filter_detail(request, name):
    """
    Get, update or delete a dynamic filter from the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dynamic_filter = r.hgetall("filter:" + str(name))
        return JSONResponse(dynamic_filter, status=200)

    if request.method == 'PUT':
        if not r.exists('filter:' + str(name)):
            return JSONResponse('Dynamic filter with name:  ' + str(name) + ' not exists.', status=404)
        data = JSONParser().parse(request)
        r.hmset('filter:' + str(name), data)
        return JSONResponse('The metadata of the dynamic filter with name: ' + str(name) + ' has been updated',
                            status=201)

    if request.method == 'DELETE':
        r.delete("filter:" + str(name))
        return JSONResponse('Dynamic filter has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


"""
Storage nodes
"""


@csrf_exempt
def list_storage_node(request):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == "GET":
        keys = r.keys("SN:*")
        print 'keys', keys
        storage_nodes = []
        for k in keys:
            sn = r.hgetall(k)
            sn["id"] = k.split(":")[1]
            storage_nodes.append(sn)
        return JSONResponse(storage_nodes, status=200)

    if request.method == "POST":
        sn_id = r.incr("storage_nodes:id")
        data = JSONParser().parse(request)
        r.hmset('SN:' + str(sn_id), data)
        return JSONResponse('Tenants group has been added in the registy', status=201)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def storage_node_detail(request, snode_id):
    """
    Get, update or delete a storage node from the registry.
    """
    try:
        r = get_redis_connection()
    except:
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


"""
Tenants group part
"""


@csrf_exempt
def add_tenants_group(request):
    """
    Add a filter with its default parameters in the registry (redis). List all the tenants groups saved in the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("G:*")
        gtenants = {}
        for key in keys:
            gtenant = r.lrange(key, 0, -1)
            gtenants[key] = gtenant
            # gtenants.extend(eval(gtenant[0]))
        return JSONResponse(gtenants, status=200)

    if request.method == 'POST':
        gtenant_id = r.incr("gtenant:id")
        data = JSONParser().parse(request)
        r.rpush('G:' + str(gtenant_id), *data)
        return JSONResponse('Tenants group has been added in the registy', status=201)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def tenants_group_detail(request, gtenant_id):
    """
    Get, update or delete a tenants group from the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        gtenant = r.lrange("G:" + str(gtenant_id), 0, -1)
        # r.hgetall("gtenants:"+str(gtenant_id))
        return JSONResponse(gtenant, status=200)

    if request.method == 'PUT':
        if not r.exists('G:' + str(gtenant_id)):
            return JSONResponse('The members of the tenants group with id:  ' + str(gtenant_id) + ' not exists.',
                                status=404)
        data = JSONParser().parse(request)
        # for tenant in data:
        r.rpush('G:' + str(gtenant_id), *data)
        return JSONResponse('The members of the tenants group with id: ' + str(gtenant_id) + ' has been updated',
                            status=201)

    if request.method == 'DELETE':
        r.delete("G:" + str(gtenant_id))
        return JSONResponse('Tenants grpup has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def gtenants_tenant_detail(request, gtenant_id, tenant_id):
    """
    Delete a member from a tenants group.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'DELETE':
        r.lrem("G:" + str(gtenant_id), str(tenant_id), 1)
        return JSONResponse('Tenant' + str(tenant_id) + 'has been deleted from group with the id: ' + str(gtenant_id),
                            status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


"""
Object Type part
"""


@csrf_exempt
def object_type_list(request):
    """
    GET: List all object types.
    POST: Bind a new object type.
    """
    try:
        r = get_redis_connection()
    except:
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
        if "types_list" not in data:
            return JSONResponse('Object type must have a types_list defining the valid object types', status=status.HTTP_400_BAD_REQUEST)

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
    except:
        return JSONResponse('Error connecting with DB', status=500)

    key = "object_type:" + object_type_name
    if request.method == 'GET':
        if r.exists(key):
            types_list = r.lrange(key, 0, -1)
            object_type = {"name": object_type_name, "types_list": types_list}
            return JSONResponse(object_type, status=200)
        return JSONResponse("Object type not found", status=404)

    if request.method == "PUT":
        if not r.exists(key):
            return JSONResponse('The object type with name: ' + object_type_name + ' does not exist.', status=404)
        data = JSONParser().parse(request)
        pipe = r.pipeline()
        # the following commands are buffered in a single atomic request (to replace current contents)
        if pipe.delete(key).rpush(key, *data).execute():
            return JSONResponse('The object type ' + str(object_type_name) + ' has been updated', status=201)
        return JSONResponse('Error storing the object type in the DB', status=500)

    if request.method == "DELETE":
        if r.exists(key):
            object_type = r.delete(key)
            return JSONResponse(object_type, status=200)
        return JSONResponse("Object type not found", status=404)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def object_type_items_detail(request, object_type_name, item_name):
    """
    Delete a extencion from a object type definition.
    """
    tenant_id = 0  # DELETE
    gtenant_id = 0  # DELETE
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'DELETE':
        r.lrem("object_type:" + str(object_type_name), str(item_name), 1)
        return JSONResponse('Tenant' + str(tenant_id) + 'has been deleted from group with the id: ' + str(gtenant_id),
                            status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def policy_list(request):
    """
    List all policies. Deploy new policies.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        if 'static' in str(request.path):
            headers = is_valid_request(request)
            if not headers:
                return JSONResponse(
                    'You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ',
                    status=status.HTTP_401_UNAUTHORIZED)
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
                                     'target_name': tenants_list[it.replace('pipeline:AUTH_', '')],
                                     'filter_name': json_value['filter_name'], 'object_type': json_value['object_type'],
                                     'object_size': json_value['object_size'],
                                     'execution_server': json_value['execution_server'],
                                     'execution_server_reverse': json_value['execution_server_reverse'],
                                     'execution_order': json_value['execution_order'], 'params': json_value['params']})
            return JSONResponse(policies, status=status.HTTP_200_OK)

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
            return JSONResponse(
                'You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ',
                status=status.HTTP_401_UNAUTHORIZED)
        rules_string = request.body.splitlines()

        for rule_string in rules_string:
            """
            Rules improved:
            TODO: Handle the new parameters of the rule
            Add containers and object in rules
            Add execution server in rules
            Add object type in rules
            """
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
    except:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    target = str(policy_id).split(':')[0]
    policy = str(policy_id).split(':')[1]

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
        data["target_name"] = tenants_list[target]
        return JSONResponse(data, status=200)
    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            policy_redis = r.hget("pipeline:AUTH_" + str(target), policy)
            json_data = json.loads(policy_redis)
            json_data.update(data)
            r.hset("pipeline:AUTH_" + str(target), policy, json.dumps(json_data))
            return JSONResponse("Data updated", status=201)
        except:
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
    except:
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
            dynamic_filter = r.hgetall("filter:" + str(action_info.filter))
            storlet = r.hgetall("storlet:" + dynamic_filter["identifier"])

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
                location = "/rule_transient/TransientRule/"
            else:
                print 'Rule:', parsed_rule
                rules[cont] = remote_host.spawn_id('policy:' + str(policy_id), 'rule', 'Rule',
                                                   [rules_to_parse[key], action_info, key, remote_host])
                location = "/rule/Rule/"

            rules[cont].start_rule()
            # Add policy into redis
            r.hmset('policy:' + str(policy_id),
                    {"id": policy_id, "policy": rule_string, "policy_description": parsed_rule,
                     "policy_location": settings.PYACTIVE_URL + location + str(policy_id), "alive": True})
            cont += 1
