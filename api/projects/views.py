from django.conf import settings
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView

from swiftclient import client as swift_client
import logging


from api.common import JSONResponse, get_redis_connection, \
    get_project_list, get_keystone_admin_auth, \
    get_admin_role_user_ids, get_swift_url_and_token


logger = logging.getLogger(__name__)


#
# Crystal Projects
#
@csrf_exempt
def projects(request, project_id=None):
    """
    GET: List all projects ordered by name
    PUT: Save a project (enable)
    DELETE: Delete a project (disable)
    POST: Check if a project exist or is enabled
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        projetcs = r.lrange('projects_crystal_enabled', 0, -1)
        return JSONResponse(projetcs, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        try:
            project_list = get_project_list()
            project_name = project_list[project_id]
            if project_name == settings.MANAGEMENT_ACCOUNT:
                return JSONResponse("Management project could not be set as Crystal project",
                                    status=status.HTTP_400_BAD_REQUEST)

            # Set Manager as admin of the Crystal Project
            keystone_client = get_keystone_admin_auth()
            admin_role_id, admin_user_id = get_admin_role_user_ids()
            keystone_client.roles.grant(role=admin_role_id, user=admin_user_id, project=project_id)

            # Post Storlet and Dependency containers
            url, token = get_swift_url_and_token(project_name)
            try:
                swift_client.put_container(url, token, "storlet")
                swift_client.put_container(url, token, "dependency")
                headers = {'X-Account-Meta-Crystal-Enabled': True, 'X-Account-Meta-Storlet-Enabled': True}
                swift_client.post_account(url, token, headers)
            except:
                pass
            # Create project docker image
            create_docker_image(r, project_id)

            r.lpush('projects_crystal_enabled', project_id)
            return JSONResponse("Data inserted correctly", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error inserting data", status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            project_list = get_project_list()
            project_name = project_list[project_id]

            # Delete Storlet and Dependency containers
            url, token = get_swift_url_and_token(project_name)
            try:
                swift_client.delete_container(url, token, "storlet")
                swift_client.delete_container(url, token, "dependency")
                headers = {'X-Account-Meta-Crystal-Enabled': '', 'X-Account-Meta-Storlet-Enabled': ''}
                swift_client.post_account(url, token, headers)
            except:
                pass
            # Delete Manager as admin of the Crystal Project
            keystone_client = get_keystone_admin_auth()
            admin_role_id, admin_user_id = get_admin_role_user_ids()
            keystone_client.roles.revoke(role=admin_role_id, user=admin_user_id, project=project_id)

            # Delete project docker image
            delete_docker_image(r, project_id)

            r.lrem('projects_crystal_enabled', project_id)
            return JSONResponse("Crystal project correctly disabled.", status=status.HTTP_201_CREATED)
        except RedisError:
            return JSONResponse("Error inserting data", status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':
        try:
            projects = r.lrange('projects_crystal_enabled', 0, -1)
            if project_id in projects:
                return JSONResponse(project_id, status=status.HTTP_200_OK)
            return JSONResponse('The project with id:  ' + str(project_id) + ' does not exist.',
                                status=status.HTTP_404_NOT_FOUND)
        except RedisError:
            return JSONResponse("Error inserting data", status=status.HTTP_400_BAD_REQUEST)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


def create_docker_image(r, project_id):
    nodes = r.keys('*_node:*')
    for node in nodes:
        node_data = r.hgetall(node)


def delete_docker_image(r, project_id):
    nodes = r.keys('*_node:*')
    for node in nodes:
        node_data = r.hgetall(node)


#
# Crystal Projects groups
#
@csrf_exempt
def add_projects_group(request):
    """
    Add a tenant group or list all the tenants groups saved in the registry.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys("project_group:*")
        project_groups = {}
        for key in keys:
            group = r.lrange(key, 0, -1)
            group_id = key.split(":")[1]
            project_groups[group_id] = group
        return JSONResponse(project_groups, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        if not data:
            return JSONResponse('Tenant group cannot be empty',
                                status=status.HTTP_400_BAD_REQUEST)
        gtenant_id = r.incr("project_groups:id")
        r.rpush('project_group:' + str(gtenant_id), *data)
        return JSONResponse('Tenant group has been added to the registry', status=status.HTTP_201_CREATED)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def projects_group_detail(request, group_id):
    """
    Get, update or delete a projects group from the registry.
    """

    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        key = 'project_group:' + str(group_id)
        if r.exists(key):
            group = r.lrange(key, 0, -1)
            return JSONResponse(group, status=status.HTTP_200_OK)
        else:
            return JSONResponse('The tenant group with id:  ' + str(group_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        key = 'project_group:' + str(group_id)
        if r.exists(key):
            data = JSONParser().parse(request)
            if not data:
                return JSONResponse('Tenant group cannot be empty',
                                    status=status.HTTP_400_BAD_REQUEST)
            pipe = r.pipeline()
            # the following commands are buffered in a single atomic request (to replace current contents)
            if pipe.delete(key).rpush(key, *data).execute():
                return JSONResponse('The members of the tenants group with id: ' + str(group_id) + ' has been updated', status=status.HTTP_201_CREATED)
            return JSONResponse('Error storing the tenant group in the DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return JSONResponse('The tenant group with id:  ' + str(group_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        key = 'project_group:' + str(group_id)
        if r.exists(key):
            r.delete("project_group:" + str(group_id))
            gtenants_ids = r.keys('G:*')
            if len(gtenants_ids) == 0:
                r.set('project_groups:id', 0)
            return JSONResponse('Tenants group has been deleted', status=status.HTTP_204_NO_CONTENT)
        else:
            return JSONResponse('The tenant group with id:  ' + str(group_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def projects_groups_detail(request, group_id, project_id):
    """
    Delete a member from a tenants group.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if request.method == 'DELETE':
        r.lrem("project_group:" + str(group_id), str(project_id), 1)
        return JSONResponse('Tenant ' + str(project_id) + ' has been deleted from group with the id: ' + str(group_id),
                            status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)
