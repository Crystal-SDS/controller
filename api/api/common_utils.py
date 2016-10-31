import logging
import os
import sys

import keystoneclient.v2_0.client as keystone_client
import redis
from django.conf import settings
from django.core.management.color import color_style
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer

from api.exceptions import FileSynchronizationException


class LoggingColors(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(LoggingColors, self).__init__(*args, **kwargs)
        self.style = self.configure_style(color_style())

    @staticmethod
    def configure_style(style):
        style.DEBUG = style.HTTP_NOT_MODIFIED
        style.INFO = style.HTTP_INFO
        style.WARNING = style.HTTP_NOT_FOUND
        style.ERROR = style.ERROR
        style.CRITICAL = style.HTTP_SERVER_ERROR
        return style

    def format(self, record):
        message = logging.Formatter.format(self, record)
        if sys.version_info[0] < 3:
            if isinstance(message, unicode):
                message = message.encode('utf-8')
        colorizer = getattr(self.style, record.levelname, self.style.HTTP_SUCCESS)
        return colorizer(message)


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


def get_token_connection(request):
    return request.META['HTTP_X_AUTH_TOKEN'] if 'HTTP_X_AUTH_TOKEN' in request.META else False


def get_keystone_admin_auth():
    admin_project = settings.MANAGEMENT_ACCOUNT
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
    keystone_url = settings.KEYSTONE_URL

    keystone = None
    try:
        keystone = keystone_client.Client(auth_url=keystone_url,
                                          username=admin_user,
                                          password=admin_passwd,
                                          tenant_name=admin_project)
    except Exception as exc:
        print(exc)

    return keystone


# def is_valid_request(request):
#     token = request.META['HTTP_X_AUTH_TOKEN']
#     is_admin = False
#     now = datetime.utcnow()
#
#     if token not in valid_tokens:
#         keystone = get_keystone_admin_auth()
#
#         try:
#             token_data = keystone.tokens.validate(token)
#         except:
#             return False
#
#         token_expiration = datetime.strptime(token_data.expires,
#                                              '%Y-%m-%dT%H:%M:%SZ')
#
#         token_roles = token_data.user['roles']
#         for role in token_roles:
#             if role['name'] == 'admin':
#                 is_admin = True
#
#         if token_expiration > now and is_admin:
#             valid_tokens[token] = token_expiration
#             return token
#
#     else:
#         token_expiration = valid_tokens[token]
#         if token_expiration > now:
#             return token
#         else:
#             valid_tokens.pop(token, None)
#
#     return False


def get_project_list():
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
        data = {'directory': directory, 'dest_directory': dest_directory, 'node_ip': node['ip'],
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
            if dictionary[arg] == 'True':
                dictionary[arg] = True
            elif dictionary[arg] == 'False':
                dictionary[arg] = False


def remove_extra_whitespaces(_str):
    return ' '.join(_str.split())
