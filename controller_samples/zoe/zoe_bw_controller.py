import json
import logging
import redis

from django.conf import settings
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from redis.exceptions import RedisError

from controllers.actors.abstract_controller import AbstractController

logger = logging.getLogger(__name__)


class ZoeBwController(AbstractController):

    _ask = ['get_target']
    _tell = ['update', 'run', 'stop_actor']

    DISK_IO_BANDWIDTH = 100.  # MBps

    def __init__(self):
        super(ZoeBwController, self).__init__()
        self.metrics = ['get_bandwidth']
        self.abstract_policies = {}
        self.bw_control = {}
        self.slo_objectives = {'platinum': int(self.DISK_IO_BANDWIDTH * 0.9),
                               'gold': int(self.DISK_IO_BANDWIDTH * 0.8),
                               'silver': int(self.DISK_IO_BANDWIDTH * 0.4),
                               'bronze': int(self.DISK_IO_BANDWIDTH * 0.2)}
        self._init_consum("zoe_queue", "zoe")
        # TODO Listen to the queue: rmq_messages to receive zoe messages --> test this in s2caio...

    # def __init__(self, name):
    #     try:
    #         self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
    #     except RedisError:
    #         print "Error connecting with Redis DB"
    #
    #     self.name = name
    #     self.zoe_metric_id = ''
    #     self.abstract_policies = {}
    #     self.bw_control = {}
    #     self.slo_objectives = {'platinum': int(self.DISK_IO_BANDWIDTH * 0.9),
    #                            'gold': int(self.DISK_IO_BANDWIDTH * 0.8),
    #                            'silver': int(self.DISK_IO_BANDWIDTH * 0.4),
    #                            'bronze': int(self.DISK_IO_BANDWIDTH * 0.2)}

    # def run(self, zoe_metric_id):
    #     """
    #     The `run()` method subscribes the controller to the Zoe metric
    #
    #     :param zoe_metric_id: The name that identifies the Zoe metric.
    #     :type zoe_metric_id: **any** String type
    #
    #     """
    #     try:
    #         self.zoe_metric_id = zoe_metric_id
    #         zoe_metric_actor = self.host.lookup(zoe_metric_id)
    #         zoe_metric_actor.attach(self.proxy)
    #
    #         #remote_host = self.host.lookup_url(settings.PYACTOR_URL, Host)  # looking up for Crystal controller existing host
    #
    #         #bw_metric_actor = remote_host.lookup('get_bandwidth')
    #         bw_metric_actor = self.host.lookup('get_bandwidth')
    #         print 'bw_metric:' + str(bw_metric_actor)
    #         logger.info('bw_metric:' + str(bw_metric_actor))
    #         bw_metric_actor.attach(self.proxy)
    #
    #     except Exception as e:
    #         raise Exception('Error attaching to metric: ' + str(e))

    @staticmethod
    def get_target():
        return 'ALL';  # Wildcard: all targets

    def update(self, metric, target, info):

        logger.info(str(metric) + " - " + str(target) + " - " + str(info))

        if metric == 'zoe_metric':
            info_dict = json.loads(info)
            logger.info("Zoe controller - Update rcvd: " + str(info_dict))
            tenant_name = info_dict['tenant']

            tenant_list = ZoeBwController.get_tenants_by_name()
            tenant_id = tenant_list[tenant_name]
            self.abstract_policies[tenant_id] = info_dict['abstract_policy']

            # Set bw objectives to redis:
            # key='SLO:bandwidth:get_bw:AUTH_366756dbfd024e0aa7f204a7498dfcfa#0'
            slo_objective = self.slo_objectives[self.abstract_policies[tenant_id]]
            self.r.set('SLO:bandwidth:get_bw:AUTH_' + tenant_id + '#0', slo_objective)
            self.r.set('SLO:bandwidth:put_bw:AUTH_' + tenant_id + '#0', slo_objective)
            self.r.set('SLO:bandwidth:ssync_bw:AUTH_' + tenant_id + '#0', slo_objective)  # not used
        elif metric == 'get_bandwidth':
            # e.g. target = 'test' or 'test/container' - info = '20.3'

            if '/' not in target:
                if target not in self.bw_control:
                    self.bw_control[target] = {'active_for': 0, 'inactive_for': 0}
                if float(info) == 0.0:
                    self.bw_control[target]['inactive_for'] += 1
                    self.bw_control[target]['active_for'] = 0
                else:
                    self.bw_control[target]['inactive_for'] = 0
                    self.bw_control[target]['active_for'] += 1
                active_tenants = self.active_tenants()
                if self.bw_control[target]['inactive_for'] == 2 and len(active_tenants) == 1:
                    # 4 seconds without requests in this tenant and there's only 1 tenant active -->
                    # disable policy

                    tenant_list = ZoeBwController.get_tenants_by_name()
                    tenant_id = tenant_list[active_tenants[0]]

                    # Obtain active policies for this tenant
                    # If there is an active bw policy --> undeploy it
                    pipeline_name = 'pipeline:' + tenant_id
                    if self.r.exists(pipeline_name):
                        pipeline_contents = self.r.hgetall(pipeline_name)
                        for key, value in pipeline_contents.items():
                            policy = json.loads(value)
                            if policy['filter_name'] == 'crystal_bandwidth_control.py':
                                logger.info("Deleting bw policy...")
                                self.r.hdel(pipeline_name, key)
                                break

    def active_tenants(self):
        active = []
        for tenant in self.bw_control.keys():
            if self.bw_control[tenant]['active_for'] > 0:
                active.append(tenant)
        return active

    @staticmethod
    def get_tenants_by_name():
        keystone_cl = ZoeBwController.get_keystone_admin_auth()
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

    def stop_actor(self):
        """
        Asynchronous method. This method can be called remotely.
        This method ends the controller execution and kills the actor.
        """
        try:
            self.host.stop_actor(self.id)
        except Exception as e:
            print e
