from controllers.actors.abstract_controller import AbstractController
import os


class StaticBandwidthPerProject(AbstractController):

    def __init__(self, method):
        super(StaticBandwidthPerProject, self).__init__()
        self.method = method
        self.metrics = [self.method+'_bandwidth']
        self.prev_assignations = dict()

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
        bw_slos = self._get_redis_slos(self.method+"_bw")

        pased_bw = {}
        assignations = {}

        for metric in metric_data:
            host = metric['host']
            project_id = metric['project_id']
            storage_policy = metric['storage_policy']

            if project_id not in pased_bw:
                pased_bw[project_id] = {}
            if storage_policy not in pased_bw[project_id]:
                pased_bw[project_id][storage_policy] = list()
            if host not in pased_bw[project_id][storage_policy]:
                pased_bw[project_id][storage_policy].append(host)

        for project_id in pased_bw:
            for storage_policy in pased_bw[project_id]:
                if project_id in bw_slos and storage_policy in bw_slos[project_id]:
                    bw = float(bw_slos[project_id][storage_policy])
                else:
                    break

                total_hosts = len(pased_bw[project_id][storage_policy])
                bw_per_host = str(round(bw/total_hosts, 1))

                if project_id not in assignations:
                    assignations[project_id] = {}
                if storage_policy not in assignations[project_id]:
                    assignations[project_id][storage_policy] = {}

                assignations[project_id][storage_policy][host] = bw_per_host

        for project_id in assignations:
            for storage_policy in assignations[project_id]:
                for host in assignations[project_id][storage_policy]:
                    updated = True
                    bw_assignation = assignations[project_id][storage_policy][host]

                    if self.prev_assignations and project_id in self.prev_assignations and \
                       storage_policy in self.prev_assignations[project_id] and host in \
                       self.prev_assignations[project_id][storage_policy]:
                        prev_bw_assignation = self.prev_assignations[project_id][storage_policy][host]
                        if bw_assignation == prev_bw_assignation:
                            updated = False

                    if updated:
                        assignation = os.path.join(project_id, self.method, storage_policy, bw_assignation)
                        self._send_message_rmq(host, assignation)

        self.prev_assignations = assignations
