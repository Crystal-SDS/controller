from abstract_metric import Metric
from threading import Thread
import datetime
import json
import socket
from copy import deepcopy


class SwiftMetric(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming', 'stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, metric_id, routing_key):
        Metric.__init__(self)

        self.queue = metric_id
        self.routing_key = routing_key
        self.name = metric_id
        self.exchange = exchange
        self.logstah_server = (self.logstash_host, self.logstash_port)
        self.last_metrics = dict()
        self.th = None
        
    def notify(self, body):
        """
        {"controller": {"AUTH_bd34c4073b65426894545b36f0d8dcce": 3}}
        """

        data = json.loads(body)
        Thread(target=self._send_data_to_logstash, args=(deepcopy(data), )).start()

        try:
            for host in data:
                del data[host]['@timestamp']
                for target in data[host]:
                    value =  data[host][target]
                    tenant = target.replace('AUTH_','')
                    if target in self._observers:
                        for observer in self._observers[tenant]:
                            observer.update(self.name, value)
        except Exception as e:
            print "Fail sending monitoring data to observer: ", e       

    def get_value(self):
        return self.value

    def _send_data_to_logstash(self, data):
        monitoring_data = dict()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for source_ip in data:   
                monitoring_data['metric_name'] = self.queue
                monitoring_data['source_ip'] = source_ip.replace('.', '-')
                monitoring_data['@timestamp'] = data[source_ip]['@timestamp']
                del data[source_ip]['@timestamp']

                for tenant, value in data[source_ip].items():                 
                    monitoring_data['metric_target'] = tenant.replace('AUTH_', '')
                    if (tenant in self.last_metrics and self.last_metrics[tenant]['value'] == 0) or tenant not in self.last_metrics:
                        monitoring_data['value'] = 0
                        current_time = monitoring_data['@timestamp']
                        date = datetime.datetime.now() - datetime.timedelta(seconds=1)
                        monitoring_data['@timestamp'] = str(date.isoformat())
                        message = json.dumps(monitoring_data)+'\n'    
                        sock.sendto(message, self.logstah_server)
                        monitoring_data['@timestamp'] = current_time

                    monitoring_data['value'] = value
                    message = json.dumps(monitoring_data)+'\n'    
                    sock.sendto(message, self.logstah_server)                  
                    self.last_metrics[tenant] = monitoring_data
                monitoring_data = dict()
        except socket.error:
            print "Error sending monitoring data to logstash"
