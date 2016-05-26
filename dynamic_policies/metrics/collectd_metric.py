from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import time

class CollectdMetric(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, metric_id, routing_key):
        Metric.__init__(self)

        self.queue = metric_id
        self.routing_key = routing_key
        self.name = metric_id
        self.exchange = exchange
        self.parser_instance = SwiftMetricsParse()
        print 'GET BW tenant initialized'
        
        # self.oh = open("/home/lab144/oh_"+metric_id+".dat", "w")
        


    def notify(self, body):
        """
        PUT VAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_bw_tenant/counter interval=5.000 1448964179.433:198
        """
        #print 'body', body
        #print '********************************************************'
        body_parsed = self.parser_instance.parse(body)
        #print 'body_parsed', body_parsed.target
        #print 'observers', self._observers.keys()
        #print '********************************************************'


        self.oh.write(str(time.time())+" "+str(len(body))+'\n')
        self.oh.flush()
        
        try:
            for observer in self._observers[body_parsed.target]:
                observer.update(self.name, body_parsed)
        except:
            #print "fail", body_parsed
            pass

    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
