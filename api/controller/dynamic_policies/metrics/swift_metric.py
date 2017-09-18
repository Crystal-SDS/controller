from abstract_metric import Metric
from threading import Thread
import logging
import json
import socket
import time
import Queue

AGGREGATION_INTERVAL = 1
logger = logging.getLogger(__name__)


class SwiftMetric(Metric):
    _tell = ['get_value', 'attach', 'detach', 'notify', 'start_consuming', 'stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach']

    def __init__(self, exchange, metric_id, routing_key):
        Metric.__init__(self)
        self.exchange = exchange
        self.queue = metric_id
        self.name = metric_id
        self.routing_key = routing_key
        self.logstash_server = (self.logstash_host, self.logstash_port)
        self.metrics = Queue.Queue()

        # Subprocess to aggregate collected metrics every time interval
        self.notifier = Thread(target=self._aggregate_and_send_info)
        self.notifier.start()

    def notify(self, body):
        """
        Method called from the consumer to indicate the value consumed from the
        rabbitmq queue. After receive the value, this value is communicated to
        all the observers subscribed to this metric.

        {'container': 'crystal/data', 'metric_name': 'bandwidth', '@timestamp': '2017-09-09T18:00:18.331492+02:00',
         'value': 16.4375, 'project': 'crystal', 'host': 'controller', 'method': 'GET', 'server_type': 'proxy'}
        """
        metric = eval(body)
        if metric['server_type'] == 'proxy':
            self.metrics.put(metric)
        self._send_data_to_logstash(metric)

    def _send_data_to_logstash(self, metric):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            message = json.dumps(metric)+'\n'
            sock.sendto(message, self.logstash_server)
        except socket.error:
            logger.info("Swift Metric: Error sending monitoring data to logstash.")

    def _aggregate_and_send_info(self):
        while True:
            time.sleep(AGGREGATION_INTERVAL)
            aggregate = dict()

            while not self.metrics.empty():
                metric = self.metrics.get()
                try:
                    project = metric['project']
                    container = metric['container']
                    value = metric['value']

                    if project not in aggregate:
                        aggregate[project] = 0
                    if container not in aggregate:
                        aggregate[container] = 0

                    aggregate[project] += value
                    aggregate[container] += value
                except:
                    logger.info("Swift Metric, Error parsing metric: " + str(metric))

            try:
                for target in aggregate:
                    if target in self._observers:
                        for observer in self._observers[target].values():
                            observer.update(self.name, aggregate[target])
            except Exception as e:
                logger.info("Swift Metric: Error sending monitoring data to observer: "+str(e))
