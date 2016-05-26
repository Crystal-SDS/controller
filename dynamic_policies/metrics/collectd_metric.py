from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
import json
import socket

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
        OLD SET:
        PUT VAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_bw_tenant/counter interval=5.000 1448964179.433:198

        NEW SET:
        {"0.0.0.0:8080": {"AUTH_bd34c4073b65426894545b36f0d8dcce": 3}}
        """
        monitoring_data = dict()
        print body
        print '********************************************************'
        data = json.loads(body)
        
        try:
            tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logstah_server_address = ("iostack.urv.cat", 5400)
            tcpsock.connect(logstah_server_address)

            for source_ip in data:
                monitoring_data['metric_name'] = self.queue
                monitoring_data['source_ip'] = source_ip.replace('.','-')
                for key, value in data[source_ip].items():
                    monitoring_data['metric_target'] = key.replace('AUTH_', '')
                    monitoring_data['value'] = value
                    tcpsock.sendall(json.dumps(monitoring_data)+'\n')
                monitoring_data = dict()
            tcpsock.close()
        except:
            pass
        
        """
        try:
            for observer in self._observers[body_parsed.target]:
                observer.update(self.name, body_parsed)
        except:
            #print "fail", body_parsed
            pass
        """

    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)
