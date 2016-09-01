from exceptions import FileSynchronizationException
from rest_framework.renderers import JSONRenderer
import keystoneclient.v2_0.client as keystone_client
from django.http import HttpResponse
from django.conf import settings
import redis
from datetime import datetime
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


def get_keystone_admin_auth():
    admin_project = settings.MANAGEMENT_ACCOUNT
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
    keystone_url = settings.KEYSTONE_URL
        
    try:
        keystone = keystone_client.Client(auth_url=keystone_url,
                                          username=admin_user,
                                          password=admin_passwd,
                                          tenant_name=admin_project)
    except Exception as e:
        print e
            
    return keystone


def is_valid_request(request):    
    token = request.META['HTTP_X_AUTH_TOKEN']
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_project = settings.MANAGEMENT_ACCOUNT
    keystone = get_keystone_admin_auth()

    try:
        token_data = keystone.tokens.validate(token)
        token_expiration = datetime.strptime(token_data.expires, '%Y-%m-%dT%H:%M:%SZ')
        now = datetime.now()
        token_user = token_data.user['name']
        token_project = token_data.tenant['name']
        
        if token_expiration > now and token_user == admin_user and admin_project == token_project:
            return token
    except:
        return False

    return False


def get_project_list(token):    
    keystone = get_keystone_admin_auth()
    tenants = keystone.tenants.list()
    
    project_list = {}
    for tenant in tenants:
        project_list[tenant.id] = tenant.name
        
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
        # print "System: %s" % rsync_command
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
