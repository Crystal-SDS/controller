from django.conf import settings
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView
from paramiko.ssh_exception import SSHException, AuthenticationException
from swiftclient import client as swift_client
import logging
import paramiko
import json
import os

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
        project_list = get_project_list()
        project_name = project_list[project_id]
        if project_name == settings.MANAGEMENT_ACCOUNT:
            return JSONResponse("Management project could not be set as Crystal project",
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            # Set Manager as admin of the Crystal Project
            keystone_client = get_keystone_admin_auth()
            admin_role_id, reseller_admin_role_id, admin_user_id = get_admin_role_user_ids()
            keystone_client.roles.grant(role=admin_role_id, user=admin_user_id, project=project_id)
            keystone_client.roles.grant(role=reseller_admin_role_id, user=admin_user_id, project=project_id)

            # Post Storlet and Dependency containers
            url, token = get_swift_url_and_token(project_name)
            swift_client.put_container(url, token, "storlet")
            swift_client.put_container(url, token, "dependency")
            headers = {'X-Account-Meta-Crystal-Enabled': True, 'X-Account-Meta-Storlet-Enabled': True}
            swift_client.post_account(url, token, headers)

            # Create project docker image
            create_docker_image(r, project_id)
            r.lpush('projects_crystal_enabled', project_id)
            return JSONResponse("Crystal Project correctly enabled", status=status.HTTP_201_CREATED)
        except:
            return JSONResponse("Error Enabling Crystal Project", status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        try:
            project_list = get_project_list()
            project_name = project_list[project_id]

            # Delete Storlet and Dependency containers
            try:
                url, token = get_swift_url_and_token(project_name)
                swift_client.delete_container(url, token, "storlet")
                swift_client.delete_container(url, token, "dependency")
                headers = {'X-Account-Meta-Crystal-Enabled': '', 'X-Account-Meta-Storlet-Enabled': ''}
                swift_client.post_account(url, token, headers)
            except:
                pass

            # Delete Manager as admin of the Crystal Project
            keystone_client = get_keystone_admin_auth()
            admin_role_id, reseller_admin_role_id, admin_user_id = get_admin_role_user_ids()
            try:
                keystone_client.roles.revoke(role=admin_role_id, user=admin_user_id, project=project_id)
                keystone_client.roles.revoke(role=reseller_admin_role_id, user=admin_user_id, project=project_id)
            except:
                pass

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
    already_created = list()
    for node in nodes:
        node_data = r.hgetall(node)
        node_ip = node_data['ip']
        if node_ip not in already_created:
            if node_data['ssh_access']:
                ssh_user = node_data['ssh_username']
                ssh_password = node_data['ssh_password']
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh_client.connect(node_ip, username=ssh_user, password=ssh_password)
                except AuthenticationException:
                    r.hset(node, 'ssh_access', False)
                    ssh_client.close()
                    logger.error('An error occurred connecting to: '+node)
                    raise AuthenticationException('An error occurred connecting to: '+node)

                try:
                    storlet_docker_image = os.path.join(settings.DOCKER_REPO, settings.STORLET_DOCKER_IMAGE)
                    project_docker_image = os.path.join(settings.DOCKER_REPO, project_id[0:13])
                    command = 'sudo docker tag '+storlet_docker_image+' '+project_docker_image
                    ssh_client.exec_command(command)
                    ssh_client.close()
                    already_created.append(node_ip)
                except SSHException:
                    ssh_client.close()
                    logger.error('An error occurred creating the Docker image in: '+node)
                    raise SSHException('An error occurred creating the Docker image in: '+node)
            else:
                logger.error('An error occurred connecting to: '+node)
                raise AuthenticationException('An error occurred connecting to: '+node)


def delete_docker_image(r, project_id):
    nodes = r.keys('*_node:*')
    already_created = list()
    for node in nodes:
        node_data = r.hgetall(node)
        node_ip = node_data['ip']
        if node_ip not in already_created:
            if node_data['ssh_access']:
                ssh_user = node_data['ssh_username']
                ssh_password = node_data['ssh_password']
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    ssh_client.connect(node_ip, username=ssh_user, password=ssh_password)
                except AuthenticationException:
                    r.hset(node, 'ssh_access', False)
                    ssh_client.close()
                    logger.error('An error occurred connecting to: '+node)
                    raise AuthenticationException('An error occurred connecting to: '+node)

                try:
                    project_docker_image = '/'.join(settings.DOCKER_REPO, project_id[0:13])
                    command = 'sudo docker rmi -f '+project_docker_image
                    ssh_client.exec_command(command)
                    ssh_client.close()
                    already_created.append(node_ip)
                except SSHException:
                    ssh_client.close()
                    logger.error('An error occurred creating the Docker image in: '+node)
                    raise SSHException('An error occurred creating the Docker image in: '+node)
            else:
                logger.error('An error occurred connecting to: '+node)
                raise AuthenticationException('An error occurred connecting to: '+node)


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
        project_groups = []
        for key in keys:
            group = r.hgetall(key)
            group['id'] = key.split(':')[1]
            group['attached_projects'] = json.loads(group['attached_projects'])
            project_groups.append(group)
        return JSONResponse(project_groups, status=status.HTTP_200_OK)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        if not data:
            return JSONResponse('Tenant group cannot be empty',
                                status=status.HTTP_400_BAD_REQUEST)
        gtenant_id = r.incr("project_groups:id")
        r.hmset('project_group:' + str(gtenant_id), data)
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
            group = r.hgetall(key)
            group['attached_projects'] = json.loads(group['attached_projects'])
            return JSONResponse(group, status=status.HTTP_200_OK)
        else:
            return JSONResponse('The tenant group with id:  ' + str(group_id) + ' does not exist.', status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        key = 'project_group:' + str(group_id)
        if r.exists(key):
            data = JSONParser().parse(request)
            try:
                r.hmset(key, data)
                return JSONResponse('The members of the tenants group with id: ' + str(group_id) + ' has been updated', status=status.HTTP_201_CREATED)
            except:
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
