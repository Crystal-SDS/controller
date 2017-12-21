from django.conf import settings
from wsgiref.util import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from swiftclient import client as swift_client
from swiftclient.exceptions import ClientException
from operator import itemgetter
import json
import logging
import mimetypes
import os

from api.common import rsync_dir_with_nodes, JSONResponse, \
    get_redis_connection, get_token_connection, make_sure_path_exists, save_file, md5,\
    to_json_bools
from api.exceptions import SwiftClientError, StorletNotFoundException, FileSynchronizationException

logger = logging.getLogger(__name__)


def check_keys(data, keys):
    return sorted(list(data)) == sorted(list(keys))


@csrf_exempt
def filter_list(request):
    """
    List all filters, or create a new one.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'GET':
        keys = r.keys("filter:*")
        filters = []
        for key in keys:
            filter = r.hgetall(key)
            to_json_bools(filter, 'get', 'put', 'post', 'head', 'delete')
            filters.append(filter)
        sorted_list = sorted(filters, key=lambda x: int(itemgetter('id')(x)))
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)

    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        if (('filter_type' not in data) or
           (data['filter_type'] == 'native' and not check_keys(data.keys(), settings.NATIVE_FILTER_KEYS[2:-1])) or
           (data['filter_type'] == 'storlet' and not check_keys(data.keys(), settings.STORLET_FILTER_KEYS[2:-1]))):
            return JSONResponse("Invalid parameters in request", status=status.HTTP_400_BAD_REQUEST)

        try:
            filter_id = r.incr("filters:id")
            data['id'] = filter_id
            r.hmset('filter:' + str(data['dsl_name']), data)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def filter_detail(request, filter_id):
    """
    Retrieve, update or delete a Filter.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not r.exists("filter:" + str(filter_id)):
        return JSONResponse('Object does not exist!', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        my_filter = r.hgetall("filter:" + str(filter_id))
        to_json_bools(my_filter, 'put', 'get', 'post', 'head', 'delete')
        return JSONResponse(my_filter, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        try:
            if 'dsl_name' in data and str(filter_id) != data['dsl_name']:
                # Check for possible activated policies
                policies = r.keys('policy:*')
                for policy_key in policies:
                    policy = r.hgetall(policy_key)
                    dsl_filter = policy['filter']
                    if dsl_filter == str(filter_id):
                        return JSONResponse("It is not possible to change the DSL Name, "+str(filter_id)+
                                            " is associated with some Dynamic Policy", status=status.HTTP_400_BAD_REQUEST)
                filter_data = r.hgetall("filter:" + str(filter_id))
                r.hmset('filter:' + str(data['dsl_name']), filter_data)
                r.delete("filter:" + str(filter_id))
                r.hmset('filter:' + str(data['dsl_name']), data)
            else:
                r.hmset('filter:' + str(filter_id), data)

            return JSONResponse("Data updated", status=status.HTTP_200_OK)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_408_REQUEST_TIMEOUT)

    elif request.method == 'DELETE':
        try:
            r.delete("filter:" + str(filter_id))

            return JSONResponse('Filter has been deleted', status=status.HTTP_204_NO_CONTENT)
        except DataError:
            return JSONResponse("Error deleting filter", status=status.HTTP_408_REQUEST_TIMEOUT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class FilterData(APIView):
    """
    Upload or get a filter data.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request, filter_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        filter_name = "filter:" + str(filter_id)
        if r.exists(filter_name):
            file_obj = request.FILES['file']

            filter_type = r.hget(filter_name, 'filter_type')
            if (filter_type == 'storlet' and not (file_obj.name.endswith('.jar') or file_obj.name.endswith('.py'))) or \
                    (filter_type == 'native' and not file_obj.name.endswith('.py')):
                return JSONResponse('Uploaded file is incompatible with filter type', status=status.HTTP_400_BAD_REQUEST)
            if filter_type == 'storlet':
                filter_dir = settings.STORLET_FILTERS_DIR
            elif filter_type == 'native':
                filter_dir = settings.NATIVE_FILTERS_DIR

            make_sure_path_exists(filter_dir)
            path = save_file(file_obj, filter_dir)
            md5_etag = md5(path)

            try:
                filter_basename = os.path.basename(path)
                content_length = os.stat(path).st_size
                etag = str(md5_etag)
                path = str(path)
                r.hset(filter_name, "filter_name", filter_basename)
                r.hset(filter_name, "path", path)
                r.hset(filter_name, "content_length", content_length)
                r.hset(filter_name, "etag", etag)
            except RedisError:
                return JSONResponse('Problems connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Update info in already deployed filters
            filter_data = r.hgetall(filter_name)
            main = filter_data['main']
            token = get_token_connection(request)
            pipelines = r.keys('pipeline:*')

            for pipeline in pipelines:
                target = pipeline.replace('pipeline:', '')
                filters_data = r.hgetall(pipeline)
                for policy_id in filters_data:
                    parameters = {}
                    parameters["policy_id"] = policy_id
                    cfilter = eval(filters_data[policy_id].replace('true', '"True"').replace('false', '"False"'))
                    if cfilter['dsl_name'] == filter_id:
                        cfilter['filter_name'] = filter_basename
                        cfilter['content_length'] = content_length
                        cfilter['etag'] = etag
                        cfilter['path'] = path
                        cfilter['main'] = main
                        set_filter(r, target, cfilter, parameters, token)

            if filter_type == 'native':
                # synchronize metrics directory with all nodes
                try:
                    rsync_dir_with_nodes(filter_dir, filter_dir)
                except FileSynchronizationException as e:
                    return JSONResponse(e.message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return JSONResponse('Filter has been updated', status=status.HTTP_201_CREATED)
        return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)

    def get(self, request, filter_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('filter:' + str(filter_id)):
            filter_path = r.hget('filter:' + str(filter_id), 'path')
            if os.path.exists(filter_path):
                filter_name = os.path.basename(filter_path)
                filter_size = os.stat(filter_path).st_size

                # Generate response
                response = StreamingHttpResponse(FileWrapper(open(filter_path), filter_size), content_type=mimetypes.guess_type(filter_path)[0])
                response['Content-Length'] = filter_size
                response['Content-Disposition'] = "attachment; filename=%s" % filter_name

                return response
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
def filter_deploy(request, filter_id, project_id, container=None, swift_object=None):
    """
    Deploy a filter to a specific swift account.
    """
    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filter_data = r.hgetall("filter:" + str(filter_id))

        if not filter_data:
            return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)

        try:
            params = JSONParser().parse(request)
        except ParseError:
            return JSONResponse("Invalid format or empty request params", status=status.HTTP_400_BAD_REQUEST)

        # Get an identifier of this new policy
        policy_id = r.incr("policies:id")

        # Set the policy data
        policy_data = {
            "policy_id": policy_id,
            "object_type": params['object_type'],
            "object_size": params['object_size'],
            "object_tag": params['object_tag'],
            "object_name": ', '.join(r.lrange('object_type:' + params['object_type'], 0, -1)),
            "execution_order": policy_id,
            "params": params['params'],
            "callable": False
        }

        if 'execution_server' in params:
            if params['execution_server'] != 'default':
                policy_data['execution_server'] = params['execution_server']

        if 'execution_server_reverse' in params:
            if params['execution_server_reverse'] != 'default':
                policy_data['execution_server_reverse'] = params['execution_server_reverse']

        if project_id.startswith('group:'):
            projects_id = json.loads(r.hgetall('project_group:' + project_id.split(':')[1])['attached_projects'])
        else:
            projects_id = [project_id]

        try:
            for project in projects_id:
                if container and swift_object:
                    target = ':'.join([project, container, swift_object])
                elif container:
                    target = ':'.join([project, container])
                else:
                    target = project

                token = get_token_connection(request)
                set_filter(r, target, filter_data.copy(), policy_data.copy(), token)

            return JSONResponse(policy_id, status=status.HTTP_201_CREATED)

        except SwiftClientError:
            return JSONResponse('Error accessing Swift.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except StorletNotFoundException:
            return JSONResponse('Storlet not found.', status=status.HTTP_404_NOT_FOUND)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def filter_undeploy(request, filter_id, project_id, container=None, swift_object=None):
    """
    Undeploy a filter from a specific swift project.
    """
    if request.method == 'PUT':

        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filter_data = r.hgetall("filter:" + str(filter_id))

        if not filter_data:
            return JSONResponse('Filter does not exist', status=status.HTTP_404_NOT_FOUND)

        if container and swift_object:
            target = project_id + "/" + container + "/" + swift_object
        elif container:
            target = project_id + "/" + container
        else:
            target = project_id

        token = get_token_connection(request)
        return unset_filter(r, target, filter_data, token)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


#
# Dependencies
#
@csrf_exempt
def dependency_list(request):
    """
    List all dependencies, or create a Dependency.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("dependency:*")
        dependencies = []
        for key in keys:
            dependencies.append(r.hgetall(key))
        return JSONResponse(dependencies, status=200)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        dependency_id = r.incr("dependencies:id")
        try:
            data["id"] = dependency_id
            r.hmset('dependency:' + str(dependency_id), data)
            return JSONResponse(data, status=201)
        except DataError:
            return JSONResponse("Error to save the filter", status=400)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_detail(request, dependency_id):
    """
    Retrieve, update or delete a Dependency.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dependency = r.hgetall("dependency:" + str(dependency_id))
        return JSONResponse(dependency, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('dependency:' + str(dependency_id), data)
            return JSONResponse("Data updated", status=201)
        except DataError:
            return JSONResponse("Error updating data", status=400)

    elif request.method == 'DELETE':
        r.delete("dependency:" + str(dependency_id))
        return JSONResponse('Dependency has been deleted', status=204)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


class DependencyData(APIView):
    parser_classes = (MultiPartParser, FormParser,)

    def put(self, request, dependency_id, format=None):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)
        if r.exists("dependency:" + str(dependency_id)):
            file_obj = request.FILES['file']
            path = save_file(file_obj, settings.DEPENDENCY_DIR)
            r.hset("dependency:" + str(dependency_id), "path", str(path))
            return JSONResponse('Dependency has been updated', status=201)
        return JSONResponse('Dependency does not exist', status=404)

    def get(self, request, dependency_id, format=None):
        # TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)


@csrf_exempt
def dependency_deploy(request, dependency_id, project_id):

    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)

        dependency = r.hgetall("dependency:" + str(dependency_id))
        if not dependency:
            return JSONResponse('Dependency does not exist', status=404)
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency["version"])}

        if "path" not in dependency.keys():
            return JSONResponse('Dependency path does not exist', status=404)

        try:
            dependency_file = open(dependency["path"], 'r')
            content_length = None
            response = dict()
            token = get_token_connection(request)
            url = settings.SWIFT_URL + "/AUTH_" + project_id
            swift_client.put_object(url, token, 'dependency', dependency["name"], dependency_file, content_length,
                                    None, None, "application/octet-stream", metadata, None, None, None, response)
        except ClientException:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            dependency_file.close()

        status = response.get('status')
        if status == 201:
            if r.exists(str(project_id) + ":dependency:" + str(dependency['name'])):
                return JSONResponse("Already deployed", status=200)

            if r.lpush(str(project_id) + ":dependencies", str(dependency['name'])):
                return JSONResponse("Deployed", status=201)

        return JSONResponse("error", status=400)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_list_deployed(request, project_id):
    if request.method == 'GET':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)

        result = r.lrange(str(project_id) + ":dependencies", 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


@csrf_exempt
def dependency_undeploy(request, dependency_id, project_id):

    if request.method == 'PUT':
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Problems to connect with the DB', status=500)

        dependency = r.hgetall("dependency:" + str(dependency_id))

        if not dependency:
            return JSONResponse('Dependency does not exist', status=404)
        if not r.exists(str(project_id) + ":dependency:" + str(dependency["name"])):
            return JSONResponse('Dependency ' + str(dependency["name"]) + ' has not been deployed already', status=404)

        try:
            token = get_token_connection(request)
            url = settings.SWIFT_URL + "/AUTH_" + project_id
            swift_response = dict()
            swift_client.delete_object(url, token, 'dependency', dependency["name"], None, None, None, None, swift_response)

        except ClientException:
            return JSONResponse(swift_response.get("reason"), status=swift_response.get('status'))

        swift_status = swift_response.get('status')

        if 200 <= swift_status < 300:
            r.delete(str(project_id) + ":dependency:" + str(dependency["name"]))
            r.lrem(str(project_id) + ":dependencies", str(dependency["name"]), 1)
            return JSONResponse('The dependency has been deleted', status=swift_status)

        return JSONResponse(swift_response.get("reason"), status=swift_status)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=405)


def set_filter(r, target, filter_data, parameters, token):
    if filter_data['filter_type'] == 'storlet':

        metadata = {"X-Object-Meta-Storlet-Language": filter_data["language"],
                    "X-Object-Meta-Storlet-Interface-Version": filter_data["interface_version"],
                    "X-Object-Meta-Storlet-Dependency": '',
                    "X-Object-Meta-Storlet-Object-Metadata": '',
                    "X-Object-Meta-Storlet-Main": filter_data["main"]
                    }

        try:
            project_id = target.split(':')[0]

            if project_id == 'global':
                projects_crystal_enabled = r.lrange('projects_crystal_enabled', 0, -1)
                for project_id in projects_crystal_enabled:
                    swift_response = dict()
                    url = settings.SWIFT_URL + "/AUTH_" + project_id
                    storlet_file = open(filter_data["path"], 'r')
                    swift_client.put_object(url, token, ".storlet",
                                            filter_data["filter_name"],
                                            storlet_file, None,
                                            None, None, "application/octet-stream",
                                            metadata, None, None, None, swift_response)
            else:
                swift_response = dict()
                url = settings.SWIFT_URL + "/AUTH_" + project_id
                storlet_file = open(filter_data["path"], 'r')
                swift_client.put_object(url, token, ".storlet",
                                        filter_data["filter_name"],
                                        storlet_file, None,
                                        None, None, "application/octet-stream",
                                        metadata, None, None, None, swift_response)
            storlet_file.close()

        except Exception as e:
            logging.error(str(e))
            raise SwiftClientError("A problem occurred accessing Swift")

        swift_status = swift_response.get("status")

        if swift_status != status.HTTP_201_CREATED:
            raise SwiftClientError("A problem occurred uploading Storlet to Swift")

    if not parameters:
        parameters = {}

    target = str(target).replace('/', ':')
    # Change 'id' key of filter
    if 'filter_id' not in filter_data:
        filter_data["filter_id"] = filter_data.pop("id")
    # Get policy id
    policy_id = parameters["policy_id"]

    del filter_data["path"]
    del parameters["policy_id"]
    # Add all filter and policy metadata to policy_id in pipeline
    data = filter_data.copy()
    data.update(parameters)

    data_dumped = json.dumps(data).replace('"True"', 'true').replace('"False"', 'false')

    r.hset("pipeline:" + str(target), policy_id, data_dumped)


# FOR TENANT:crystal DO DELETE compression
def unset_filter(r, target, filter_data, token):
    if filter_data['filter_type'] == 'storlet':
        try:
            project_id = target.split('/', 3)[0]
            swift_response = dict()
            url = settings.SWIFT_URL + "/AUTH_" + project_id
            swift_client.delete_object(url, token, ".storlet", filter_data["filter_name"], None, None, None, None, swift_response)
        except ClientException as e:
            print swift_response + str(e)
            return swift_response.get("status")

    target = target.replace('/', ':')
    keys = r.hgetall("pipeline:" + str(target))
    for key, value in keys.items():
        json_value = json.loads(value)
        if json_value["filter_name"] == filter_data["filter_name"]:
            r.hdel("pipeline:" + str(target), key)
