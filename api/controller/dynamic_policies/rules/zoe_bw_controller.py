import json
import redis

from django.conf import settings
from redis.exceptions import RedisError
import keystoneclient.v2_0.client as keystone_client


class ZoeBwController(object):

    _sync = {}
    _async = ['update', 'run', 'stop_actor']
    _ref = []
    _parallel = []

    DISK_IO_BANDWIDTH = 70.  # MBps

    def __init__(self, name):
        try:
            self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            print "Error connecting with Redis DB"

        self.name = name
        self.workload_metric_id = ''
        self.abstract_policies = {}
        self.slo_objectives = {'platinum': int(self.DISK_IO_BANDWIDTH * 0.9),
                               'gold': int(self.DISK_IO_BANDWIDTH * 0.8),
                               'silver': int(self.DISK_IO_BANDWIDTH * 0.4),
                               'bronze': int(self.DISK_IO_BANDWIDTH * 0.2)}

    def run(self, workload_metric_id):
        """
        The `run()` method subscribes the controller to the Zoe metric

        :param workload_metric_id: The name that identifies the workload metric.
        :type workload_metric_id: **any** String type

        """
        try:
            self.workload_metric_id = workload_metric_id
            metric_actor = self.host.lookup(workload_metric_id)
            metric_actor.attach(self.proxy)
        except Exception as e:
            raise Exception('Error attaching to metric bw_info: ' + str(e))

    def update(self, metric, info):

        if metric == 'zoe_metric':
            info_dict = json.loads(info)
            print("Zoe controller - Update rcvd: " + str(info_dict))
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

    @staticmethod
    def get_tenants_by_name():
        keystone = ZoeBwController.get_keystone_admin_auth()
        tenants = keystone.tenants.list()

        tenant_list = {}
        for tenant in tenants:
            tenant_list[tenant.name] = tenant.id

        return tenant_list

    @staticmethod
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

    # def stop_actor(self):
    #     """
    #     Asynchronous method. This method can be called remotely.
    #     This method ends the controller execution and kills the actor.
    #     """
    #     try:
    #         if self.workload_metric_id:
    #             metric_actor = self.host.lookup(self.workload_metric_id)
    #             metric_actor.detach_global_obs()
    #
    #         self._atom.stop()
    #
    #     except Exception as e:
    #         logger.error(str(e))
    #         print e