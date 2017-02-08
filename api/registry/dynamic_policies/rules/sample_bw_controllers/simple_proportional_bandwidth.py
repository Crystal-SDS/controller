import sys

# from registry.dynamic_policies.rules.base_global_controller import AbstractEnforcementAlgorithm
from registry.dynamic_policies.rules.base_bw_controller import BaseBwController


class SimpleProportionalBandwidthPerTenant(BaseBwController):

    def compute_algorithm(self, info):
        """
        Simple compute algorithm
        """
        assign = dict()
        bw_a = dict()

        # bw = self._get_redis_bw()
        slo_name = self.method.lower() + "_bw"  # get_bw or put_bw
        bw = self._get_redis_slos(slo_name)

        for account in info:
            assign[account] = dict()
            bw_a[account] = dict()
            for ip in info[account]:
                for policy in info[account][ip]:
                    for device in info[account][ip][policy]:
                        if policy not in assign[account]:
                            assign[account][policy] = dict()
                        if device not in assign[account][policy]:
                            assign[account][policy][device] = dict()
                        if 'requests' not in assign[account][policy][device]:
                            assign[account][policy][device]['requests'] = 1
                        else:
                            assign[account][policy][device]['requests'] += 1
                        if 'ips' not in assign[account][policy][device]:
                            assign[account][policy][device]['ips'] = set()
                        assign[account][policy][device]['ips'].add(ip)
                          
            for policy in assign[account]:
                for device in assign[account][policy]:
                    for ip in assign[account][policy][device]['ips']:
                        try:
                            bw_a[account][ip+"-"+policy+"-"+device] = float(bw[account][policy])/assign[account][policy][device]['requests']
                        except Exception:
                            # TODO: NO CONTINUE
                            print "Error calculating bandwidth in simple_proportional_bandwidth rule: " + str(sys.exc_info()[0])
                          
        return bw_a
