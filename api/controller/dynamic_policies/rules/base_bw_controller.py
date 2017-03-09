from controller.dynamic_policies.rules.base_global_controller import AbstractEnforcementAlgorithm


class BaseBwController(AbstractEnforcementAlgorithm):

    def _get_redis_slos(self, slo_name):
        """
        Gets the SLOs from the redis database
        """
        slos = dict()
        keys = self.r.keys("SLO:bandwidth:" + slo_name + ":*")
        for key in keys:
            target = key.rsplit(':', 1)[1]
            project, policy_id = target.split('#')
            #project_id = project.split('_')[1]
            #if project_id not in slos:
            if project not in slos:
                slos[project] = dict()
            slos[project][policy_id] = self.r.get(key)
        return slos
