from abstract_metric import Metric
from metrics_parser import SwiftMetricsParse
from threading import Thread
import datetime
import json
import socket
import time


class SwiftMetric(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, exchange, metric_id, routing_key, state='stateless'):
        Metric.__init__(self)

        self.queue = metric_id
        self.routing_key = routing_key
        self.name = metric_id
        self.exchange = exchange
        self.state = state
        self.parser_instance = SwiftMetricsParse()
        self.logstah_server = ("iostack.urv.cat", 5400)
        self.last_metrics = dict()
        self.th = None
        
    def notify(self, body):
        """
        {"0.0.0.0:8080": {"AUTH_bd34c4073b65426894545b36f0d8dcce": 3}}
        """

        data = json.loads(body)

        if self.state == 'stateful':
            self._register_metric(data)
            if not self.th:
                self.th = Thread(target=self._send_data_to_logstash_periodically)
                self.th.start() 
        else:
            Thread(target=self._send_data_to_logstash,args=(data, )).start()
            
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
    
    def _register_metric(self, data):
        monitoring_data = dict()
        for source_ip in data:
            for key, value in data[source_ip].items():
                monitoring_data['metric_target'] = key.replace('AUTH_', '')
                monitoring_data['metric_name'] = self.queue
                monitoring_data['source_ip'] = source_ip.replace('.','-')
                
                if key not in self.last_metrics:
                    monitoring_data['value'] = int(value)
                else:
                    monitoring_data['value'] = self.last_metrics[key]['value'] + int(value)
                
                self.last_metrics[key] = monitoring_data

    def _send_data_to_logstash(self, data):
        monitoring_data = dict()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for source_ip in data:
                monitoring_data['metric_name'] = self.queue
                monitoring_data['source_ip'] = source_ip.replace('.','-')
                for key, value in data[source_ip].items():
                                            
                    monitoring_data['metric_target'] = key.replace('AUTH_', '')
  
                    if (key in self.last_metrics and self.last_metrics[key]['value'] == 0) or key not in self.last_metrics:
                        monitoring_data['value'] = 0
                        date = datetime.datetime.now() - datetime.timedelta(seconds=1)
                        monitoring_data['@timestamp'] = str(date.isoformat())
                        message = json.dumps(monitoring_data)+'\n'    
                        sock.sendto(message, self.logstah_server)
                        
                    monitoring_data['value'] = value
                    if '@timestamp' in monitoring_data:
                        del monitoring_data['@timestamp']
                    message = json.dumps(monitoring_data)+'\n'    
                    sock.sendto(message, self.logstah_server)                    
                    self.last_metrics[key] = monitoring_data
                    
                monitoring_data = dict()
        except:
            print "Error sending monitoring data to logstash"
            pass
    
    
    def _send_data_to_logstash_periodically(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while True:
                time.sleep(1)
                for key in self.last_metrics:
                    message = json.dumps(self.last_metrics[key])+'\n'    
                    sock.sendto(message, self.logstah_server)
        except:
            print "Error sending monitoring data to logstash"
            pass
