from base_bw_rule import AbstractEnforcementAlgorithm

class SimpleProportionalReplicationBandwidth(AbstractEnforcementAlgorithm):


    def _get_redis_bw(self):
        """
        Gets the bw assignation from the redis database
        """            
        return float(self.r.get("replication_bw"))
    
    def compute_algorithm(self, info):
        """
        Simple compute algorithm for replication
        """
        bw_a = dict()
        bw = self._get_redis_bw()
        total_ssync_requests = 0
        #Example: {u'storage5:6000': {u'source:192.168.2.21': {u'sdb1': 655350.0}}, u'storage4:6000': {u'source:192.168.2.23': {u'sdb1': 983025.0}}}
        #Example: {u'storage5:6000': {u'source:192.168.2.23': {u'sdb1': 2621400.0}, u'source:192.168.2.21': {u'sdb1': 1638375.0}}}

        for node in info:
            total_ssync_requests += len(info[node])
        
        bw_x_request = bw/total_ssync_requests

        for node in info:
            bw_a[node] = dict()
            for source in info[node]:
                bw_a[node][source] = bw_x_request
                          
        return bw_a
    
    def send_results(self, assign):
        """
        Sends the calculated BW to each Node that has active requests
        """
        for node in assign:
            for source in assign[node]:        
                new_flow = node not in self.last_bw or source not in self.last_bw[node]
                if not new_flow and float(assign[node][source]) == float(self.last_bw[node][source]):
                    break
                address = node+'/'+source+'/'+self.method+'/None/None/'+str(round(assign[node][source],1))
                routing_key = '.'+node.replace('.','-').replace(':','-') + "."
                print "BW CHANGED: "+ str(address) 
                self.send_message_rmq(address, routing_key)
