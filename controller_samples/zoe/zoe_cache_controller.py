import json
import logging
import requests
import time

from django.conf import settings
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
import swiftclient

from controllers.actors.abstract_controller import AbstractController

logger = logging.getLogger(__name__)

CACHE_SIZE = 500*1024*1024
PREFETCH_SIZE = 300*1024*1024
CONTAINER = "ebooks"  # hardcoded
PREFETCH_PATH = "/mnt/ssd/prefetch"
CACHE_PATH = "/mnt/ssd/cache"
CONTROLLER_URL = "http://controller:9000"
DSL_NAME_CACHING = "caching"
DSL_NAME_PREFETCHING = "prefetchingzoe"


class ZoeCacheController(AbstractController):

    _ask = []
    _tell = ['run', 'stop_actor', 'notify']

    def __init__(self):
        super(ZoeCacheController, self).__init__()
        self.abstract_policies = {}
        self.token = None

    def run(self):
        """
        Entry Method
        """
        self._init_consum("zoe_queue", "zoe")

    def compute_rmq_message(self, body):
        logger.info('Zoe_cache... in notify body='+str(body))
        tenant_name, abstract_policy = body.split(':')

        tenant_list = ZoeCacheController.get_tenants_by_name()
        logger.info('Tenant list: ' + str(tenant_list))
        tenant_id = tenant_list[tenant_name]
        self.abstract_policies[tenant_id] = abstract_policy

        # Provisional approach:
        # platinum/gold/silver = iterative
        # bronze = not iterative

        # Only apply cache/prefetching for iterative approaches (apps that use the same data at every run)
        logger.info(self.abstract_policies[tenant_id])
        if self.abstract_policies[tenant_id] in ['platinum', 'gold', 'silver']:
            # Let's analyze dataset size
            try:
                container_size = self.obtain_container_size(tenant_name, CONTAINER)
                logger.info("container_size is " + str(container_size))
                logger.info("CACHE_SIZE is " + str(CACHE_SIZE))

                if container_size < CACHE_SIZE:
                    # If caching policy is not active, the controller activates it
                    caching_policy_active = False
                    pipeline_name = 'pipeline:' + tenant_id + ':' + CONTAINER
                    if self.redis.exists(pipeline_name):
                        pipeline_contents = self.redis.hgetall(pipeline_name)
                        for key, value in pipeline_contents.items():
                            policy = json.loads(value)
                            if policy['filter_name'] == 'crystal_cache_control.py':
                                caching_policy_active = True

                    if not caching_policy_active:
                        # TODO Create a caching policy for this tenant
                        params = {"cache_max_size": str(CACHE_SIZE),
                                  "cache_path": CACHE_PATH,
                                  "eviction_policy": "LFU"}
                        self.activate_policy(tenant_id + '/' + CONTAINER, DSL_NAME_CACHING, self._format_params(params))
                        logger.info("Caching policy activated for " + tenant_name + "/" + CONTAINER)

                else:
                    # If prefetch policy is not active, the controller activates it
                    prefetching_policy_active = False
                    pipeline_name = 'pipeline:' + tenant_id + ':' + CONTAINER
                    if self.redis.exists(pipeline_name):
                        pipeline_contents = self.redis.hgetall(pipeline_name)
                        for key, value in pipeline_contents.items():
                            policy = json.loads(value)
                            if policy['dsl_name'] == DSL_NAME_PREFETCHING:
                                prefetching_policy_active = True

                    if not prefetching_policy_active:
                        # TODO Create a prefetching policy for this tenant
                        params = {"cache_max_size": str(PREFETCH_SIZE),
                                  "cache_path": PREFETCH_PATH,
                                  "eviction_policy": "LFU",
                                  "tenant_id": tenant_id,
                                  "container": CONTAINER}
                        self.activate_policy(tenant_id + '/' + CONTAINER, DSL_NAME_PREFETCHING, self._format_params(params))
                        logger.info("Prefetching policy activated for " + tenant_name + "/" + CONTAINER)

                        time.sleep(3)

                        # Send a dummy request to initialize prefetching
                        self._send_dummy_request(tenant_name, CONTAINER)

            except Exception as exc:
                logger.error(exc.message)

    @staticmethod
    def _format_params(params_dict):
        return ','.join([x + '=' + y for x, y in params_dict.items()])

    @staticmethod
    def get_tenants_by_name():
        keystone_cl = ZoeCacheController.get_keystone_admin_auth()
        projects = keystone_cl.projects.list()

        tenants_by_name = {}
        for project in projects:
            tenants_by_name[project.name] = project.id

        return tenants_by_name

    @staticmethod
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
           logger.error(str(exc))

        return keystone_client

    def obtain_container_size(self, tenant_name, container_name):
        # Swift request to obtain container size
        admin_user = settings.MANAGEMENT_ADMIN_USERNAME
        admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
        keystone_url = settings.KEYSTONE_ADMIN_URL

        swift = swiftclient.client.Connection(authurl=keystone_url, user=admin_user, key=admin_passwd,
                                              tenant_name=tenant_name, auth_version='3')
        container = swift.get_container(container_name, limit=1)
        container_size = int(container[0]['x-container-bytes-used'])
        swift.close()
        return container_size

    def activate_policy(self, target_id, dsl_name, params):
        if not self.token:
            self._get_admin_token()

        headers = {"X-Auth-Token": self.token}

        url = CONTROLLER_URL + "/filters/" + target_id + "/deploy/" + dsl_name

        data = dict()
        data['object_type'] = ''
        data['object_size'] = ''
        data['params'] = params

        response = requests.put(url, json.dumps(data), headers=headers)

        if 200 <= response.status_code < 300:
            logger.info('Policy applied')
        else:
            logger.error("Policy deployment failed: " + str(response.content))
            raise Exception()

    def _get_admin_token(self):
        """
        Method called to obtain the admin credentials, which we need to made requests to controller
        """
        admin_project = settings.MANAGEMENT_ACCOUNT
        admin_user = settings.MANAGEMENT_ADMIN_USERNAME
        admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
        admin_keystone_url = settings.KEYSTONE_ADMIN_URL
        try:
            _, self.token = swiftclient.client.get_auth(admin_keystone_url,
                                       admin_project + ":" + admin_user,
                                       admin_passwd, auth_version="3")
        except:
            logger.error("There was an error getting a token from keystone")
            raise Exception()

    def _send_dummy_request(self, tenant_name, container_name):
        # Send a dummy Swift GET request
        admin_user = settings.MANAGEMENT_ADMIN_USERNAME
        admin_passwd = settings.MANAGEMENT_ADMIN_PASSWORD
        keystone_url = settings.KEYSTONE_ADMIN_URL

        swift = swiftclient.client.Connection(authurl=keystone_url, user=admin_user, key=admin_passwd,
                                              tenant_name=tenant_name, auth_version='3')
        container = swift.get_container(container_name, limit=1)
        dummy_file_name = container[1][0]['name']
        swift.get_object(container_name, dummy_file_name)
        swift.close()
