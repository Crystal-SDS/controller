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
            project_id = metric['project_id']
            method = metric['method']
            storage_policy = metric['storage_policy']


            if project_id in bw_slos and storage_policy in bw_slos[project_id]:
                bw = bw_slos[project_id][storage_policy]

            
            
            
            #bw = str(round(calculated_bw, 1))

            bw = bw_slos[project_id][storage_policy]

            assignation = os.path.join(project_id, method, storage_policy, bw)
            self._send_message_rmq(host, assignation)
