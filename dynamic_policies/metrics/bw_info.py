from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
from threading import Thread
import json
import time

class BwInfo(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', \
            'stop_actor', 'get_redis_bw', 'compute_assignations', 'parse_osinfo', 'send_bw']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, queue, routing_key, name):
        Metric.__init__(self)

        self.queue = queue
        self.routing_key = routing_key
        self.name = name
        self.exchange = exchange
        self.parser_instance = SwiftMetricsParse()
        print name+' initialized'
        self.count = {}
        self.last_bw = {}
        self.bw_observer = None

        '''Log for experimental purposes'''
        self.output = open("/home/lab144/tenant_bw_experiment.dat", "w")

        '''Subprocess to aggregate collected metrics every time interval'''
        self.notifier = Thread(target=self.aggregate_and_send_info)
        self.notifier.start()

    def attach(self, observer, bw_obs):
        """
        Asyncronous method. This method allows to be called remotelly. It is called from
        observers in order to subscribe in this workload metric. This observer will be
        saved in a dictionary type structure where the key will be the tenant assigned in the observer,
        and the value will be the PyActive proxy to connect to the observer.
        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        if bw_obs:
            self.bw_observer = observer
        else:
            tenant, policy = observer.get_topic_subsribe()
            if not tenant in self._observers.keys():
                self._observers[tenant] = {}
                if not policy in self._observers[tenant].keys():
                    self._observers[tenant][policy] = set()
            if not observer in self._observers[tenant][policy]:
                self._observers[tenant][policy].add(observer)

    def notify(self, body):
        self.parse_osinfo(body)

    def aggregate_and_send_info(self):
        while True:
            '''Aggregate parsed data'''
            aggregated_results = self.count
            self.count = dict()
            output_line = ''
            
            for tenant in aggregated_results:
                aggregated_bw = 0.0
                for ip in aggregated_results[tenant]:
                    for policy in aggregated_results[tenant][ip]:
                        for device in aggregated_results[tenant][ip][policy]:
                            aggregated_bw += aggregated_results[tenant][ip][policy][device]
            
                print "TENANT " + tenant + " -> " + str(aggregated_bw)
                output_line += str(aggregated_bw) + '\t'
                print >> self.output, output_line

            '''Notify of raw monitoring info to distributed enforcement algorithms'''
            if self.bw_observer and aggregated_results:
                self.bw_observer.update(self.name, aggregated_results)
        
            '''Notify to simple observers of aggregated values (policy actors)'''
            for tenant in self._observers.keys():
                if tenant in aggregated_results.keys():
                    #print "TENANT: ", tenant
                    for policy, observers in self._observers[tenant].items():
                        if policy in aggregated_results[tenant].keys():
                            for observer in observers:
                                observer.update(self.name, aggregated_results[tenant][policy]["bw"])
                                #print "---> AGGREGATED BW: ", aggregated_results[tenant][policy]["bw"]
            time.sleep(1)

    def parse_osinfo(self, osinfo):
        os = json.loads(osinfo)
        for ip in os:
            for tenant in os[ip]:
                for policy in os[ip][tenant]:
                    for device in os[ip][tenant][policy]:
                        if not tenant in self.count:
                            self.count[tenant] = {}
                        if not ip in self.count[tenant]:
                            self.count[tenant][ip] = {}
                        if not policy in self.count[tenant][ip]:
                            self.count[tenant][ip][policy] = {}
                        self.count[tenant][ip][policy][device] = os[ip][tenant][policy][device]

    def get_value(self):
        return self.value
