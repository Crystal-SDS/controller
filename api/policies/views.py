from django.conf import settings
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from operator import itemgetter
import logging
import json
import os
import re
import dsl_parser
from api.common import JSONResponse, get_redis_connection, get_project_list, \
    get_token_connection, create_local_host, rule_actors, to_json_bools
from api.exceptions import SwiftClientError, StorletNotFoundException, \
    ProjectNotFound, ProjectNotCrystalEnabled
from filters.views import set_filter, unset_filter
logger = logging.getLogger(__name__)


@csrf_exempt
def policy_list(request):
    """
    List all policies (sorted by execution_order). Deploy new policies via DSL.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        if 'static' in str(request.path):
            project_list = get_project_list()
            project_list['global'] = 'Global'
            keys = r.keys("pipeline:*")
            policies = []
            for it in keys:
                for key, value in r.hgetall(it).items():
                    policy = json.loads(value)
                    filter = r.hgetall('filter:' + str(policy['dsl_name']))
                    to_json_bools(filter, 'get', 'put', 'post', 'head', 'delete')
                    target_id = it.replace('pipeline:', '')
                    policies.append({'id': key, 'target_id': target_id,
                                     'target_name': project_list[target_id.split(':')[0]],
                                     'filter_name': policy['filter_name'],
                                     'object_type': policy['object_type'],
                                     'object_size': policy['object_size'],
                                     'object_tag': policy['object_tag'],
                                     'execution_server': policy['execution_server'],
                                     'reverse': policy['reverse'],
                                     'execution_order': policy['execution_order'],
                                     'params': policy['params'],
                                     'put': filter['put'],
                                     'get': filter['get'],
                                     'post': filter['post'],
                                     'head': filter['head'],
                                     'delete': filter['delete']})
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
        # New Policy
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
                    http_host = request.META['HTTP_HOST']
                    deploy_dynamic_policy(r, rule_string, rule_parsed, http_host)
                else:
                    # Static Rule
                    deploy_static_policy(request, r, rule_parsed)

            except SwiftClientError:
                return JSONResponse('Error accessing Swift.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except StorletNotFoundException:
                return JSONResponse('Storlet not found.', status=status.HTTP_404_NOT_FOUND)

            except ProjectNotFound:
                return JSONResponse('Invalid Project Name/ID. The Project does not exist.', status=status.HTTP_404_NOT_FOUND)
            except ProjectNotCrystalEnabled:
                return JSONResponse('The project is not Crystal Enabled. Verify it in the Projects panel.',
                                    status=status.HTTP_404_NOT_FOUND)
            except Exception:
                return JSONResponse('Please, review the rule, and start the related workload '
                                    'metric before creating a new policy', status=status.HTTP_401_UNAUTHORIZED)

        return JSONResponse('Policies added successfully!', status=status.HTTP_201_CREATED)

    if request.method == 'PUT':
        # Dynamic Policy From form
        http_host = request.META['HTTP_HOST']
        data = JSONParser().parse(request)

        policy_id = r.incr("policies:id")
        rule_id = 'policy:' + str(policy_id)

        action = data['action']
        project_id = data['project_id']
        container = data['container_id']

        if project_id == 'global':
            project_name = 'Global'
        else:
            project_list = get_project_list()
            project_name = project_list[project_id]

        if container:
            target_id = os.path.join(project_id, container)
            target_name = os.path.join(project_name, container)
        else:
            target_id = project_id
            target_name = project_name

        if data['transient']:
            location = settings.RULE_TRANSIENT_MODULE
        else:
            location = settings.RULE_MODULE
        policy_location = os.path.join(settings.PYACTOR_URL, location, str(rule_id))

        policy_data = {"id": policy_id,
                       "target_id": target_id,
                       "target_name": target_name,
                       "filter": data['filter_id'],
                       "parameters": data['params'],
                       "action": action,
                       "condition": data['workload_metric']+' '+data['condition'],
                       "object_type": data['object_type'],
                       "object_size": data['object_size'],
                       "object_tag": data['object_tag'],
                       "transient": data['transient'],
                       "policy_location": policy_location,
                       "status": 'Alive'}

        start_dynamic_policy_actor(policy_data, http_host)

        try:
            r.hmset(rule_id, policy_data)
            return JSONResponse("Policy inserted correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error inserting policy", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Static Policies
#
@csrf_exempt
def static_policy_detail(request, policy_id):
    """
    Retrieve, update or delete a static policy.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    target = str(policy_id).split(':')[:-1]
    target = ':'.join(target)
    policy = str(policy_id).split(':')[-1]

    if request.method == 'GET':
        project_list = get_project_list()
        project_list['global'] = 'Global'
        policy_redis = r.hget("pipeline:" + str(target), policy)
        data = json.loads(policy_redis)
        filter = r.hgetall('filter:' + str(data['dsl_name']))
        to_json_bools(filter, 'get', 'put', 'post', 'head', 'delete')
        data['get'] = filter['get']
        data['put'] = filter['put']
        data['post'] = filter['post']
        data['head'] = filter['head']
        data['delete'] = filter['delete']
        data["id"] = policy
        data["target_id"] = target
        data["target_name"] = project_list[target.split(':')[0]]
        return JSONResponse(data, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            policy_redis = r.hget("pipeline:" + str(target), policy)
            json_data = json.loads(policy_redis)
            json_data.update(data)
            json_data['execution_order'] = int(json_data['execution_order'])
            r.hset("pipeline:" + str(target), policy, json.dumps(json_data))
            return JSONResponse("Data updated", status=201)
        except DataError:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.hdel('pipeline:' + target, policy)

        policies_ids = r.keys('policy:*')
        pipelines_ids = r.keys('pipeline:*')
        if len(policies_ids) == 0 and len(pipelines_ids) == 0:
            r.set('policies:id', 0)
        # token = get_token_connection(request)
        # unset_filter(r, target, filter_data, token)

        return JSONResponse('Policy has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


def deploy_static_policy(request, r, parsed_rule):
    token = get_token_connection(request)
    container = None
    rules_to_parse = dict()
    projects_crystal_enabled = r.lrange('projects_crystal_enabled', 0, -1)
    project_list = get_project_list()

    for target in parsed_rule.target:
        if target[0] == 'TENANT':
            project = target[1]
        elif target[0] == 'CONTAINER':
            project, container = target[1].split('/')

        if project in project_list:
            # Project ID
            project_id = project
        elif project in project_list.values():
            # Project name
            project_id = project_list.keys()[project_list.values().index(project)]
        else:
            raise ProjectNotFound()

        if project_id not in projects_crystal_enabled:
            raise ProjectNotCrystalEnabled()

        if container:
            target = os.path.join(project_id, container)
        else:
            target = project_id

        rules_to_parse[target] = parsed_rule

    for target in rules_to_parse.keys():
        for action_info in rules_to_parse[target].action_list:
            logger.info("Static policy, target rule: " + str(action_info))

            cfilter = r.hgetall("filter:"+str(action_info.filter))

            if not cfilter:
                return JSONResponse("Filter does not exist", status=status.HTTP_404_NOT_FOUND)

            if action_info.action == "SET":

                # Get an identifier of this new policy
                policy_id = r.incr("policies:id")

                # Set the policy data
                policy_data = {
                    "policy_id": policy_id,
                    "object_type": "",
                    "object_size": "",
                    "object_tag": "",
                    "execution_order": policy_id,
                    "params": "",
                    "callable": False
                }

                # Rewrite default values
                if parsed_rule.object_list:
                    if parsed_rule.object_list.object_type:
                        policy_data["object_type"] = parsed_rule.object_list.object_type.object_value
                    if parsed_rule.object_list.object_size:
                        policy_data["object_size"] = [parsed_rule.object_list.object_size.operand,
                                                      parsed_rule.object_list.object_size.object_value]
                if action_info.server_execution:
                    policy_data["execution_server"] = action_info.server_execution
                if action_info.params:
                    policy_data["params"] = action_info.params
                if action_info.callable:
                    policy_data["callable"] = True

                # Deploy (an exception is raised if something goes wrong)
                set_filter(r, target, cfilter, policy_data, token)

            elif action_info.action == "DELETE":
                unset_filter(r, target, cfilter, token)


#
# Dynamic Policies
#
@csrf_exempt
def dynamic_policy_detail(request, policy_id):
    """
    Delete a dynamic policy.
    """
    http_host = request.META['HTTP_HOST']
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    key = 'policy:' + str(policy_id)

    if request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            if data['status'] == 'Stopped':
                policy_id = int(policy_id)
                if policy_id in rule_actors:
                    rule_actors[policy_id].stop_actor()
                    del rule_actors[policy_id]
            else:
                policy_data = r.hgetall(key)
                try:
                    start_dynamic_policy_actor(policy_data, http_host)
                except Exception as e:
                    return JSONResponse(str(e), status=400)

            r.hmset(key, data)
            return JSONResponse("Data updated", status=201)
        except DataError:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        try:
            policy_id = int(policy_id)
            if policy_id in rule_actors:
                rule_actors[policy_id].stop_actor()
                del rule_actors[policy_id]
        except:
            logger.info("Error stopping the rule actor: "+str(policy_id))

        r.delete(key)
        policies_ids = r.keys('policy:*')
        pipelines_ids = r.keys('pipeline:*')
        if len(policies_ids) == 0 and len(pipelines_ids) == 0:
            r.set('policies:id', 0)
        return JSONResponse('Policy has been deleted', status=204)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


def deploy_dynamic_policy(r, rule_string, parsed_rule, http_host):
    rules_to_parse = dict()
    project = None
    container = None
    # TODO: get only the Crystal enabled projects
    projects_crystal_enabled = r.lrange('projects_crystal_enabled', 0, -1)
    project_list = get_project_list()

    for target in parsed_rule.target:
        if target[0] == 'TENANT':
            project = target[1]
        elif target[0] == 'CONTAINER':
            project, container = target[1].split('/')

        if project in project_list:
            # Project ID
            project_id = project
            project_name = project_list[project_id]
        elif project in project_list.values():
            # Project name
            project_name = project
            project_id = project_list.keys()[project_list.values().index(project)]
        else:
            raise ProjectNotFound()

        if project_id not in projects_crystal_enabled:
            raise ProjectNotCrystalEnabled()

        if container:
            target = project_name+":"+os.path.join(project_id, container)
            # target = crystal:f1bf1d778939445dbd20734cbd98de16/data
        else:
            target = project_name+":"+project_id
            # target = crystal:f1bf1d778939445dbd20734cbd98de16

        rules_to_parse[target] = parsed_rule

    for target in rules_to_parse.keys():
        for action_info in rules_to_parse[target].action_list:
            container = None
            if '/' in target:
                # target includes a container
                project, container = target.split('/')
                project_name, project_id = project.split(':')
                target_id = os.path.join(project_id, container)
                target_name = os.path.join(project_name, container)
            else:
                target_name, target_id = target.split(':')

            policy_id = r.incr("policies:id")
            rule_id = 'policy:' + str(policy_id)

            if action_info.transient:
                transient = True
                location = settings.RULE_TRANSIENT_MODULE
            else:
                transient = False
                location = settings.RULE_MODULE
            policy_location = os.path.join(settings.PYACTOR_URL, location, str(rule_id))

            # FIXME Should we recreate a static rule for each target and action??
            condition_re = re.compile(r'.* (WHEN .*) DO .*', re.M | re.I)
            condition_str = condition_re.match(rule_string).group(1)

            object_type = ""
            object_size = ""
            object_tag = ""
            if parsed_rule.object_list:
                if parsed_rule.object_list.object_type:
                    object_type = parsed_rule.object_list.object_type.object_value
                if parsed_rule.object_list.object_tag:
                    object_type = parsed_rule.object_list.object_tag.object_value
                if parsed_rule.object_list.object_size:
                    object_size = [parsed_rule.object_list.object_size.operand,
                                   parsed_rule.object_list.object_size.object_value]

            policy_data = {"id": policy_id,
                           "target_id": target_id,
                           "target_name": target_name,
                           "filter": action_info.filter,
                           "parameters": action_info.params,
                           "action": action_info.action,
                           "condition": condition_str.replace('WHEN ', ''),
                           "object_type": object_type,
                           "object_size": object_size,
                           "object_tag": object_tag,
                           "transient": transient,
                           "policy_location": policy_location,
                           "status": 'Alive'}

            start_dynamic_policy_actor(policy_data, http_host)

            # Add policy into Redis
            r.hmset('policy:' + str(policy_id), policy_data)


def start_dynamic_policy_actor(policy_data, http_host):
    to_json_bools(policy_data, 'transient')
    host = create_local_host()
    transient = policy_data["transient"]
    policy_id = int(policy_data["id"])
    rule_id = 'policy:' + str(policy_id)
    if transient:
        rule_actors[policy_id] = host.spawn(rule_id, settings.RULE_TRANSIENT_MODULE, policy_data, http_host)
    else:
        rule_actors[policy_id] = host.spawn(rule_id, settings.RULE_MODULE, policy_data, http_host)
    try:
        rule_actors[policy_id].start_rule()
    except Exception as e:
        rule_actors[policy_id].stop_actor()
        del rule_actors[policy_id]
        raise ValueError("An error occurred starting the policy actor: "+str(e))


#
# Access Control
#
@csrf_exempt
def access_control(request):

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)
    
    if request.method == 'GET':
        acl = [] 
        try:
            keys = r.keys('access_control:*')
            for key in keys:
                policy = r.hgetall(key)
                policy['id'] = key.split(':', 1)[1]
                to_json_bools(policy, 'write', 'read')
                acl.append(policy)
                
            keys = r.hgetall('access_controls:project_id')
            for key in keys:
                print keys[key]
                policy = json.loads(keys[key])
                policy['id'] = "access_controls:project_id:" + key
                to_json_bools(policy, 'write', 'read')
                acl.append(policy)
        except DataError:
            return JSONResponse("Error retrieving policy", status=400)
        return JSONResponse(acl, status=status.HTTP_200_OK)


    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            
            if data['container_id']:
                key = 'access_control:' + data['project_id'] + ':' + data['container_id']
                r.hmset(key, data)
            else:
                key = str(r.incr('access_controls:id'))
                r.hset('access_controls:project_id', key, json.dumps(data))
                
            return JSONResponse("Access control policy created", status=201)
        except DataError:
            return JSONResponse("Error creating policy", status=400)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def access_control_detail(request, policy_id):
    """
    Delete a access control.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)
    
    if request.method == 'GET':
        
        try:
            if policy_id.startswith('access_controls:project_id:'):
                key = str(policy_id.split(':')[2])
                if key in r.hgetall('access_controls:project_id'):
                    acl = (r.hgetall('access_controls:project_id'))[key]
                    data = json.loads(acl)
                    to_json_bools(data, 'write', 'read')
                    return JSONResponse(data, status=status.HTTP_200_OK)                
                else:
                    return JSONResponse("ACL not found.", status=status.HTTP_404_NOT_FOUND)
            else:
                key = 'access_control:' + policy_id
                if r.keys(key):
                    data = r.hgetall(key)
                    to_json_bools(data, 'write', 'read')
                    return JSONResponse(data, status=status.HTTP_200_OK)                
                else:
                    return JSONResponse("ACL not found.", status=status.HTTP_404_NOT_FOUND)       
        except DataError:
            return JSONResponse("Error retrieving policy", status=400)
    
    if request.method == 'DELETE':
        acl = [] 
        try:
            if policy_id.startswith('access_controls:project_id:'):
                r.hdel('access_controls:project_id', str(policy_id.split(':')[2]))
                if not r.hgetall('access_controls:project_id'):
                    r.delete('access_controls:id')
            else:
                r.delete('access_control:' + policy_id)
        except DataError:
            return JSONResponse("Error retrieving policy", status=400)
        return JSONResponse(acl, status=status.HTTP_200_OK)
    
   
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            if policy_id.startswith('access_controls:project_id:'):
                key = str(policy_id.split(':')[2])
                if key in r.hgetall('access_controls:project_id'):
                    r.hset('access_controls:project_id', key, data)
                    return JSONResponse('Data updated', status=status.HTTP_201_CREATED)
                else:
                    return JSONResponse("ACL not found.", status=status.HTTP_404_NOT_FOUND)
            else:
                key = 'access_control:' + policy_id
                if r.keys(key):
                    r.hmset(key, data)
                    return JSONResponse('Data updated', status=status.HTTP_201_CREATED)
                else:
                    return JSONResponse("ACL not found.", status=status.HTTP_404_NOT_FOUND)
        except DataError:
            return JSONResponse("Error creating policy", status=400)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


#
# Bandwidth SLO's
#
@csrf_exempt
def slo_list(request):
    """
    List all SLOs, or create an SLO.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        slos = []
        keys = r.keys('SLO:*')
        for key in keys:
            _, dsl_filter, slo_name, target = key.split(':')
            value = r.get(key)
            slos.append({'dsl_filter': dsl_filter, 'slo_name': slo_name, 'target': target, 'value': value})
        return JSONResponse(slos, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            slo_key = ':'.join(['SLO', data['dsl_filter'], data['slo_name'], data['target']])
            r.set(slo_key, data['value'])

            return JSONResponse(data, status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse('Error saving SLA.', status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def slo_detail(request, dsl_filter, slo_name, target):
    """
    Retrieve, update or delete SLO.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    slo_key = ':'.join(['SLO', dsl_filter, slo_name, target])

    if request.method == 'GET':
        if r.exists(slo_key):
            value = r.get(slo_key)
            slo = {'dsl_filter': dsl_filter, 'slo_name': slo_name, 'target': target, 'value': value}
            return JSONResponse(slo, status=status.HTTP_200_OK)
        else:
            return JSONResponse("SLO not found.", status=status.HTTP_404_NOT_FOUND)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.set(slo_key, data['value'])
            return JSONResponse('Data updated', status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse('Error updating data', status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        r.delete(slo_key)
        return JSONResponse('SLA has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Object Type
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
