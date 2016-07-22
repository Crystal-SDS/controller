from exceptions import FileSynchronizationException
from rest_framework.renderers import JSONRenderer
from swiftclient import client as swift_client
from django.http import HttpResponse
from django.conf import settings
import requests
import redis
import json
import os


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """

    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)


def get_crystal_admin_token():

    admin_project = settings.MANAGEMENT_ACCOUNT
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
    keystone_url = settings.KEYSTONE_URL
    
    try:
        _, token = swift_client.get_auth(keystone_url, 
                                         admin_project+":"+admin_user, 
                                         admin_passwd,
                                         auth_version="2.0")
    except Exception as e:
        print e
            
    return token


def get_project_list():    
    token = get_crystal_admin_token()
    keystone_response = requests.get(settings.KEYSTONE_URL + "/tenants", headers={'X-Auth-Token':token})
    keystone_projects = json.loads(keystone_response.content)["tenants"]

    project_list = {}
    for project in keystone_projects:
        project_list[project["id"]] = project["name"]
        
    return project_list
        
        
def rsync_dir_with_nodes(directory):
    # retrieve nodes
    nodes = get_all_registered_nodes()
    for node in nodes:
        if not node.viewkeys() & {'ssh_username', 'ssh_password'}:
            raise FileSynchronizationException("SSH credentials missing for some Swift node")

        # The basename of the path is not needed because it will be the same as source dir
        dest_directory = os.path.dirname(directory)
        data = {'directory':  directory, 'dest_directory': dest_directory, 'node_ip': node['ip'],
                'ssh_username': node['ssh_username'], 'ssh_password': node['ssh_password']}
        rsync_command = 'sshpass -p {ssh_password} rsync --progress --delete -avrz -e ssh {directory} {ssh_username}@{node_ip}:{dest_directory}'.format(**data)
        print "System: %s" % rsync_command
        ret = os.system(rsync_command)
        if ret != 0:
            raise FileSynchronizationException("An error occurred copying files to Swift nodes")


def get_all_registered_nodes():
    """
    Returns all registered nodes
    :return:
    """
    r = get_redis_connection()
    keys = r.keys("node:*")
    nodes = []
    for key in keys:
        node = r.hgetall(key)
        nodes.append(node)
    return nodes


def to_json_bools(dictionary, *args):
    for arg in args:
        if arg in dictionary:
            dictionary[arg] = (dictionary[arg] == 'True')


def remove_extra_whitespaces(_str):
    return ' '.join(_str.split())
