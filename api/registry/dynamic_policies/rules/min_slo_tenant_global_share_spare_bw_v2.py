from base_bw_rule import AbstractEnforcementAlgorithm


class MinTenantSLOGlobalSpareBWShare(AbstractEnforcementAlgorithm):

    DISK_IO_BANDWIDTH = 70.  # MBps
    PROXY_IO_BANDWIDTH = 1250.  # MBps
    NUM_PROXYS = 1
    NUM_SN = 3

    def compute_algorithm(self, info):

        monitoring_info = self._format_monitoring_info(info)

        disk_usage = dict()
        # 1ST STAGE: Get the appropriate assignments to achieve the SLOs to QoS tenants
        bw_enforcements = self._get_redis_bw()

        # Work without policies at this moment
        clean_bw_enforcements = dict()
        for tenant in bw_enforcements:
            clean_bw_enforcements[tenant] = 0
            for policy in bw_enforcements[tenant]:
                clean_bw_enforcements[tenant] += int(bw_enforcements[tenant][policy])
        bw_enforcements = clean_bw_enforcements

        qos_computed_assignments = self.min_slo_assignments(monitoring_info, disk_usage, bw_enforcements)
        # print "FIX QOS: ", qos_computed_assignments

        # 2ND STAGE: Calculate new assignments to all tenants to share the spare bw globally
        total_bw_assigned = 0.0
        for disk_id in disk_usage.keys():
            for tenant in disk_usage[disk_id]:
                total_bw_assigned += sum(disk_usage[disk_id][tenant])

        # available_bw = (self.NUM_PROXYS*self.PROXY_IO_BANDWIDTH)-total_bw_assigned
        available_bw = min((self.NUM_PROXYS*self.PROXY_IO_BANDWIDTH)-total_bw_assigned, (self.NUM_SN*self.DISK_IO_BANDWIDTH)-total_bw_assigned)
        spare_bw_enforcements = dict()

        # print "\n--> Available BW:", available_bw

        # Share globally the spare bw across existing tenants
        for tenant in monitoring_info.keys():
            spare_bw_enforcements[tenant] = available_bw/len(monitoring_info.keys())

        # print "SP_BW_EN : ", spare_bw_enforcements
        # print

        qos_computed_assignments = self.min_slo_assignments(monitoring_info, disk_usage, spare_bw_enforcements)

        return qos_computed_assignments

    def min_slo_assignments(self, monitoring_info, disk_usage, bw_enforcements):
        computed_assignments = dict()
        # First, sort tenants depending on the amount of transfers they are doing
        sorted_tenants = sorted(monitoring_info.items(), key=lambda t: len(t[1]))

        # FIRST STAGE, SIMPLE ALLOCATION OF QOS TENANTS
        # Allocation iteration based on the first fit decreasing strategy
        for (tenant, previous_assignments) in sorted_tenants:

            # print "Tenant: ", tenant, " PA:", previous_assignments
            # Initialize assignment entry for this tenant
            if tenant not in computed_assignments:
                computed_assignments[tenant] = dict()
            for (disk_id, transfer_speed) in previous_assignments:
                assert transfer_speed >= -1, "NEGATIVE TRANSFER SPEED!!" + str(transfer_speed)
                # Initialize disk usage dicts
                if disk_id not in computed_assignments[tenant]:
                    computed_assignments[tenant][disk_id] = 0
                if disk_id not in disk_usage:
                    disk_usage[disk_id] = dict()
                if tenant not in disk_usage[disk_id]:
                    disk_usage[disk_id][tenant] = []
                # Now, only work with QoS tenants
                if tenant not in bw_enforcements.keys():
                    disk_usage[disk_id][tenant].append(0)
                    continue
                # Get the slot per transfer of this tenant in the optimal case
                tenatative_assignment = bw_enforcements[tenant]/float(len(previous_assignments))
                # computed_assignments[tenant][disk_id] += tenatative_assignment
                # bw for this disk and this tenant
                disk_usage[disk_id][tenant].append(tenatative_assignment)

        # print "Disk Usage: ", disk_usage
        # SUM BW
        for disk_id in disk_usage:
            for tenant in disk_usage[disk_id]:
                computed_assignments[tenant][disk_id] = sum(disk_usage[disk_id][tenant])

        # print "-- Computed assignments: ", computed_assignments
        surplus = 0
        for tenant in computed_assignments:
            for disk_id in computed_assignments[tenant]:
                disk_load = computed_assignments[tenant][disk_id]
                if disk_load > self.DISK_IO_BANDWIDTH:
                    surplus += computed_assignments[tenant][disk_id] - self.DISK_IO_BANDWIDTH
                    computed_assignments[tenant][disk_id] = self.DISK_IO_BANDWIDTH

        # print "Surplus: ", surplus
        # print "-- Computed assignments: ", computed_assignments

        return computed_assignments

    def _format_monitoring_info(self, info):
        """
        Arrange and simplify the obtained monitoring info for the algorithm
        """
        formatted_info = dict()
        for account in info:
            formatted_info[account] = []
            for ip in info[account]:
                for policy in info[account][ip]:
                    for device in info[account][ip][policy]:
                        disk_id = ip + "-" + policy + "-" + device
                        formatted_info[account].append((disk_id, info[account][ip][policy][device]))

        return formatted_info
