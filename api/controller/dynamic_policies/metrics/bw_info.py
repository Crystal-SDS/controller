from abstract_metric import Metric
from threading import Thread
import json
import time

AGGREGATION_INTERVAL = 0.2


class BwInfo(Metric):
    _tell = ['get_value', 'attach', 'detach', 'notify', 'start_consuming', 'stop_consuming', 'init_consum',
             'stop_actor', 'get_redis_bw', 'compute_assignations', 'parse_osinfo', 'send_bw', 'detach_global_obs']
    _ref = ['attach']

    def __init__(self, exchange, queue, routing_key, method):
        Metric.__init__(self)

        self.queue = queue
        self.routing_key = routing_key
        self.name = queue
        self.exchange = exchange
        self.method = method
        print '{0} initialized'.format(queue)
        self.count = {}
        self.last_bw = {}
        self.bw_observer = None

        # Log for experimental purposes
        # self.output = open("/home/lab144/bw_experiment_"+method+".dat", "w")
        self.last_bw_info = list()
        self.bw_info_to_average = int(1/AGGREGATION_INTERVAL)

        # TODELETE:
        # self.oh = open("/home/lab144/oh_"+method+".dat", "w")

        # Subprocess to aggregate collected metrics every time interval
        self.notifier = Thread(target=self.aggregate_and_send_info)
        self.notifier.start()

    # TODO REFACTORING: Discrimination between automation controllers and global controllers in attach/detach
    # must be moved to Swift_Metric, because it's something generic to all metrics. All metrics receive
    # a dict with raw data that can be exploited by global controllers
    def attach(self, observer, bw_obs):
        """
        Asynchronous method. This method allows to be called remotely. It is called from
        observers in order to subscribe in this workload metric. This observer will be
        saved in a dictionary type structure where the key will be the tenant assigned in the observer,
        and the value will be the PyActor proxy to connect to the observer.
        :param observer: The PyActor proxy of the observer rule that calls this method.
        :type observer: **any** PyActor Proxy type
        """
        if bw_obs:
            self.bw_observer = observer
        else:
            tenant, policy = observer.get_topic_subsribe()
            if tenant not in self._observers.keys():
                self._observers[tenant] = {}
                if policy not in self._observers[tenant].keys():
                    self._observers[tenant][policy] = set()
            if observer not in self._observers[tenant][policy]:
                self._observers[tenant][policy].add(observer)

    # TODO New method
    def detach_global_obs(self):
        self.bw_observer = None

    def notify(self, body):
        # self.oh.write(str(time.time())+" "+str(len(body))+'\n')
        # self.oh.flush()
        self.parse_osinfo(body)

    def aggregate_and_send_info(self):
        while True:
            # Aggregate parsed data
            aggregated_results = self.count
            self.count = dict()

            # TODO REFACTORING: Remove this if not needed
            if aggregated_results:
                self._write_experimental_results(aggregated_results)

            # TODO REFACTORING: This discrimination must be in swift_metric because it is orthogonal
            # Notify of raw monitoring info to distributed enforcement algorithms
            if self.bw_observer and aggregated_results:
                # print "updating bw_observer with " + str(aggregated_results)
                self.bw_observer.update(self.name, aggregated_results)

            # Notify to simple observers of aggregated values (policy actors)
            for tenant in self._observers.keys():
                if tenant in aggregated_results.keys():
                    # print "TENANT: ", tenant
                    for policy, observers in self._observers[tenant].items():
                        if policy in aggregated_results[tenant].keys():
                            for observer in observers:
                                observer.update(self.name, aggregated_results[tenant][policy]["bw"])
                                # print "---> AGGREGATED BW: ", aggregated_results[tenant][policy]["bw"]
            time.sleep(AGGREGATION_INTERVAL)

    def parse_osinfo(self, osinfo):
        os = json.loads(osinfo)

        for ip in os:
            for tenant in os[ip]:
                for policy in os[ip][tenant]:
                    for device in os[ip][tenant][policy]:
                        if tenant not in self.count:
                            self.count[tenant] = {}
                        if ip not in self.count[tenant]:
                            self.count[tenant][ip] = {}
                        if policy not in self.count[tenant][ip]:
                            self.count[tenant][ip][policy] = {}
                        self.count[tenant][ip][policy][device] = os[ip][tenant][policy][device]

    def _write_experimental_results(self, aggregated_results):
        """
        This method writes aggregated results to the specified output. It is mainly used for experimental purposes.
        :param aggregated_results: A dictionary of aggregated results.
        :return:
        """
        if len(self.last_bw_info) == self.bw_info_to_average:
            averaged_aggregated_results = dict()
            for tmp_result in self.last_bw_info:
                for tenant in tmp_result:
                    if tenant not in averaged_aggregated_results:
                        averaged_aggregated_results[tenant] = 0.0
                    for ip in tmp_result[tenant]:
                        for policy in tmp_result[tenant][ip]:
                            for device in tmp_result[tenant][ip][policy]:
                                averaged_aggregated_results[tenant] += tmp_result[tenant][ip][policy][device]
            """
            for tenant in averaged_aggregated_results:
                value = averaged_aggregated_results[tenant]/self.bw_info_to_average
                print "TENANT " + tenant + " " + self.method + " -> " + str("{:,}".format(value))
                # self.output.write(tenant+"\t"+str(time.time())+"\t"+str(averaged_aggregated_results[tenant]/self.bw_info_to_average)+"\n")
                # self.output.flush()
            """
            self.last_bw_info = list()

        # Aggregate results for further averages
        self.last_bw_info.append(aggregated_results)
