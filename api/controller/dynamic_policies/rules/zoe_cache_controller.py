import json
import logging
import redis

from django.conf import settings
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ZoeCacheController(object):

    _ask = []
    _tell = ['update', 'run', 'stop_actor']

    DISK_IO_BANDWIDTH = 100.  # MBps

    def __init__(self, name):
        try:
            self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            print "Error connecting with Redis DB"

        self.name = name
        self.zoe_metric_id = ''
        self.abstract_policies = {}

    def run(self, zoe_metric_id):
        """
        The `run()` method subscribes the controller to the Zoe metric

        :param zoe_metric_id: The name that identifies the Zoe metric.
        :type zoe_metric_id: **any** String type

        """
        try:
            self.zoe_metric_id = zoe_metric_id
            zoe_metric_actor = self.host.lookup(zoe_metric_id)
            zoe_metric_actor.attach(self.proxy)

        except Exception as e:
            raise Exception('Error attaching to metric: ' + str(e))

    def update(self, metric, target, info):

        logger.info(str(metric) + " - " + str(target) + " - " + str(info))

        if metric == 'zoe_metric':
            info_dict = json.loads(info)
            logger.info("Zoe controller - Update rcvd: " + str(info_dict))
            tenant_name = info_dict['tenant']

            tenant_list = ZoeCacheController.get_tenants_by_name()
            tenant_id = tenant_list[tenant_name]
            self.abstract_policies[tenant_id] = info_dict['abstract_policy']

            # Naive approach: apply cache to tenant >= gold
            # If caching policy is not active, the controller activates it
            caching_policy_active = False
            pipeline_name = 'pipeline:' + tenant_id
            if self.r.exists(pipeline_name):
                pipeline_contents = self.r.hgetall(pipeline_name)
                for key, value in pipeline_contents.items():
                    policy = json.loads(value)
                    if policy['filter_name'] == 'crystal_cache_control.py':
                        caching_policy_active = True

            if not caching_policy_active:
                # TODO Create a caching policy for this tenant


    def stop_actor(self):
        """
        Asynchronous method. This method can be called remotely.
        This method ends the controller execution and kills the actor.
        """
        try:
            self.host.stop_actor(self.id)
        except Exception as e:
            print e

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
            print(exc)

        return keystone_client