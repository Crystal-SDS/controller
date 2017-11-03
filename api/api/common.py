from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from django.conf import settings
from django.core.management.color import color_style
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
from api.exceptions import FileSynchronizationException
from pyactor.context import set_context, create_host
from swiftclient import client as swift_client
import threading
import errno
import hashlib
import calendar
import logging
import redis
import os
import sys
import time

logger = logging.getLogger(__name__)
host = None
NODE_STATUS_THRESHOLD = 15  # seconds

controller_actors = dict()
metric_actors = dict()
rule_actors = dict()


class LoggingColorsDjango(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(LoggingColorsDjango, self).__init__(*args, **kwargs)
        self.style = self.configure_style(color_style())

    @staticmethod
    def configure_style(style):
        style.DEBUG = style.HTTP_NOT_MODIFIED
        style.INFO = style.HTTP_SUCCESS
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


class LoggingColorsCrystal(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(LoggingColorsCrystal, self).__init__(*args, **kwargs)
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
    keystone_url = settings.KEYSTONE_ADMIN_URL

    keystone_client = None
    try:
        auth = v3.Password(auth_url=keystone_url,
                           username=admin_user,
                           password=admin_passwd,
                           project_name=admin_project,
                           user_domain_id='default',
                           project_domain_id='default')
        sess = session.Session(auth=auth)
        keystone_client = client.Client(session=sess)
    except Exception as exc:
        print(exc)

    return keystone_client


def get_swift_url_and_token(project_name):
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
    keystone_url = settings.KEYSTONE_ADMIN_URL

    return swift_client.get_auth(keystone_url,
                                 project_name + ":"+admin_user,
                                 admin_passwd, auth_version="3")


def get_admin_role_user_ids(keystone_client):
    # keystone_client = get_keystone_admin_auth()
    roles = keystone_client.roles.list()
    for role in roles:
        if role.name == 'admin':
            admin_role_id = role.id
        if role.name == 'ResellerAdmin':
            reseller_admin_role_id = role.id
    users = keystone_client.users.list()
    for user in users:
        if user.name == settings.MANAGEMENT_ADMIN_USERNAME:
            admin_user_id = user.id

    return admin_role_id, reseller_admin_role_id, admin_user_id


def get_project_list():
    keystone_client = get_keystone_admin_auth()
    projects = keystone_client.projects.list()

    project_list = {}
    for project in projects:
        project_list[project.id] = project.name

    return project_list


def rsync_dir_with_nodes(directory):
    # retrieve nodes
    nodes = get_all_registered_nodes()
    already_sync = list()
    for node in nodes:
        if node['ip'] not in already_sync:
            already_sync.append(node['ip'])
            to_json_bools(node, 'ssh_access')
            if not node['ssh_access']:
                raise FileSynchronizationException("SSH credentials missing. Please, set the credentials for this "+node['type']+" node: "+node['name'])

            # The basename of the path is not needed because it will be the same as source dir
            logger.info("Rsync - pushing to "+node['type']+":"+node['name'])
            dest_directory = os.path.dirname(directory)
            data = {'directory': directory, 'dest_directory': dest_directory, 'node_ip': node['ip'],
                    'ssh_username': node['ssh_username'], 'ssh_password': node['ssh_password']}

            threading.Thread(target=rsync, args=(node, data)).start()


def rsync(node, data):
    rsync_command = 'sshpass -p {ssh_password} rsync --progress --delete -avrz -e ssh {directory} {ssh_username}@{node_ip}:{dest_directory}'.format(**data)
    os.system(rsync_command)


def get_all_registered_nodes():
    """
    Returns all registered nodes
    :return:
    """
    r = get_redis_connection()
    keys = r.keys("*_node:*")
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


def create_local_host():
    global host
    try:
        set_context()
        host = create_host(settings.PYACTOR_URL)
        logger.info("Controller PyActor host created")
    except:
        pass

    return host


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def save_file(file_, path=''):
    """
    Helper to save a file
    """
    filename = file_.name
    file_path = os.path.join(path, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)
    fd = open(str(path) + "/" + str(filename), 'wb')
    for chunk in file_.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) + "/" + str(filename)


def delete_file(filename, path):
    """
    Helper to save a file
    """
    file_path = os.path.join(path, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)
    pyc = file_path+"c"
    if os.path.isfile(pyc):
        os.remove(pyc)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
