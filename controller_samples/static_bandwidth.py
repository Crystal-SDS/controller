from controllers.actors.abstract_controller import AbstractController
import os


class StaticBandwidthPerProject(AbstractController):

    metrics = ['get_bandwidth']

    def _get_redis_slos(self, slo_name):
        """
        Gets the SLOs from the redis database
        """
        slos = dict()
        keys = self.redis.keys("SLO:bandwidth:" + slo_name + ":*")
        for key in keys:
            target = key.rsplit(':', 1)[1]
            project, policy_id = target.split('#')
            if project not in slos:
                slos[project] = dict()
            slos[project][policy_id] = self.redis.get(key)
        return slos

    def compute_data(self, metric_data):
        bw_slos = self._get_redis_slos("get_bw")

        for metric in metric_data:
            host = metric['host']
            project = metric['project']
            method = metric['method']
            # storage_policy = metric['storage_policy']
            calculated_bw = metric['value']
            bw = str(round(calculated_bw, 1))

            print host, project, method, calculated_bw

            #assignation = os.path.join(project, method, storage_policy, bw)
            #self._send_message_rmq(host, assignation)

