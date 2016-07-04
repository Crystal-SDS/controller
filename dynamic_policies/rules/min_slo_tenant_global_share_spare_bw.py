"""
Created on Apr 18, 2016

@author: raul
"""
from base_bw_rule import AbstractEnforcementAlgorithm


class MinTenantSLOGlobalSpareBWShare(AbstractEnforcementAlgorithm):
    
    DISK_IO_BANDWIDTH = 100.  # MBps
    PROXY_IO_BANDWIDTH = 100.  # MBps
    NUM_PROXYS = 1

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
        
        # 2ND STAGE: Calculate new assignments to all tenants to share the spare bw globally
        total_bw_assigned = 0.0
        for disk_id in disk_usage.keys():
            for tenant in disk_usage[disk_id]:
                total_bw_assigned += sum(disk_usage[disk_id][tenant])
        free_proxy_bw = (self.NUM_PROXYS*self.PROXY_IO_BANDWIDTH)-total_bw_assigned
        spare_bw_enforcements = dict()
        
        # Share globally the spare bw across existing tenants
        for tenant in monitoring_info.keys():
            spare_bw_enforcements[tenant] = free_proxy_bw/len(monitoring_info.keys())

        non_qos_computed_assignments = self.min_slo_assignments(monitoring_info, disk_usage, spare_bw_enforcements)
                
        # 3ND STAGE: Sum the assignments of SLO and spare BW
        for tenant in non_qos_computed_assignments:
            if tenant not in qos_computed_assignments:
                qos_computed_assignments[tenant] = dict() 
            for disk in non_qos_computed_assignments[tenant]:
                if disk not in qos_computed_assignments[tenant]:
                    qos_computed_assignments[tenant][disk] = 0
                qos_computed_assignments[tenant][disk] += non_qos_computed_assignments[tenant][disk]                   
        return qos_computed_assignments
    
    def min_slo_assignments(self, monitoring_info, disk_usage, bw_enforcements):
        computed_assignments = dict()
        # First, sort tenants depending on the amount of transfers they are doing
        sorted_tenants = sorted(monitoring_info.items(), key=lambda t: len(t[1]))
        
        # FIRST STAGE, SIMPLE ALLOCATION OF QOS TENANTS
        # Allocation iteration based on the first fit decreasing strategy
        for (tenant, previous_assignments) in sorted_tenants:   
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
                computed_assignments[tenant][disk_id] = tenatative_assignment
                # bw for this disk and this tenant
                disk_usage[disk_id][tenant].append(tenatative_assignment) 
        
        # SECOND STAGE, CHECK FOR REALLOCATION OF QOS TENANTS TO MEET MINIMUM BW
        # Get disks of QoS tenants in disks that are overloaded
        overloaded_disks = dict()    
        for disk_id in sorted(disk_usage):
            disk_load = 0
            for tenant in disk_usage[disk_id]:
                disk_load += sum(disk_usage[disk_id][tenant])
            if disk_load > self.DISK_IO_BANDWIDTH:
                overloaded_disks[disk_id] = disk_load
                
        # Redistribute assignments of QoS tenants in overloaded disks to meet minimum BW
        for disk_id in overloaded_disks.keys():
            to_redistribute = overloaded_disks[disk_id] - self.DISK_IO_BANDWIDTH
            qos_tenants_for_this_disk = [t for t in disk_usage[disk_id].keys() if t in bw_enforcements.keys()]
            # We can reassign bw for those tenants with requests in other disks
            tenants_to_redistribute = [t for t in qos_tenants_for_this_disk if len(computed_assignments[t].keys()) > 1]
            # Do redistribution of tenants with alternative disks
            for offload_tenant in tenants_to_redistribute:
                if to_redistribute <= 0:
                    break
                for offload_disk in computed_assignments[offload_tenant]:
                    if to_redistribute <= 0:
                        break
                    if offload_disk == disk_id:
                        continue
                    # Check the load of the alternative disk
                    disk_load = 0
                    for t in disk_usage[offload_disk]:
                        disk_load += sum(disk_usage[offload_disk][t])
                    assert disk_load >= 0, disk_load
                    # If the alternative disk has spare bandwidth
                    if disk_load >= self.DISK_IO_BANDWIDTH:
                        continue
                    # Get the spare bw of the alternative disk
                    available_for_redistribute = min(self.DISK_IO_BANDWIDTH-disk_load,
                                                     sum(disk_usage[disk_id][offload_tenant]),
                                                     to_redistribute)
                    # Calculate the increase of the share of this tenant on the alternative disk
                    increase_bw_slot = available_for_redistribute/float(len(disk_usage[offload_disk][offload_tenant]))
                    # Increase share of this tenant in the alternative disk
                    disk_usage[offload_disk][offload_tenant] = \
                        [(x + increase_bw_slot) for x in disk_usage[offload_disk][offload_tenant]]
                    computed_assignments[offload_tenant][offload_disk] += increase_bw_slot
                    # Decrease share of this tenant in the overloaded disk
                    decrease_bw_slot = available_for_redistribute/len(disk_usage[disk_id][offload_tenant])
                    disk_usage[disk_id][offload_tenant] = \
                        [(x - decrease_bw_slot) for x in disk_usage[disk_id][offload_tenant]]
                    computed_assignments[offload_tenant][disk_id] -= decrease_bw_slot
                    # Recalculate the amount of bw to redistribute in the overloaded disk
                    to_redistribute -= available_for_redistribute

            # If the disk is still overloaded, then reduce the assignment to each storage node
            if to_redistribute > 0:
                reduce_bw_slot = 0
                # Calculate the amount of bw to subtract for QoS tenant requests
                converged = False
                while not converged:
                    current_useless_tenants = [t for t in qos_tenants_for_this_disk
                                               if computed_assignments[t][disk_id] < reduce_bw_slot]
                    qos_disk_connections = 0
                    for tenant in qos_tenants_for_this_disk:
                        if tenant in current_useless_tenants:
                            continue
                        qos_disk_connections += len(disk_usage[disk_id][tenant])
                    # This represents the bw to be subtracted to each QoS tenant transfer to meet the maximum disk capacity
                    reduce_bw_slot = to_redistribute/(float(qos_disk_connections))
                    updated_useless_tenants = len([t for t in qos_tenants_for_this_disk
                                                   if computed_assignments[t][disk_id] < reduce_bw_slot])
                    if len(current_useless_tenants) == updated_useless_tenants: 
                        converged = True                        
                # Reduce the share of QoS tenants in the overloaded disk
                for tenant in qos_tenants_for_this_disk:
                    if reduce_bw_slot > computed_assignments[tenant][disk_id]:
                        continue
                    disk_usage[disk_id][tenant] = [(x - reduce_bw_slot) for x in disk_usage[disk_id][tenant]]
                    computed_assignments[tenant][disk_id] -= reduce_bw_slot
                    
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
