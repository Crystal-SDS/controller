from django.conf import settings
from redis.exceptions import RedisError
from threading import Thread
import logging
import redis
import json
import socket
import time
import Queue

AGGREGATION_INTERVAL = 1
logger = logging.getLogger(__name__)


class SwiftMetric(object):
    """
    Metric: This class is the responsible to consume
    messages from RabbitMQ and send the data to each observer subscribed to it.
    This class also treats each tenant as a topic, so it is able to distinguish
    for each observer in that tenant is subscribed. In this way, the metric
    actor only sends the necessary information to each observer.
    """
    _tell = ['attach', 'detach', 'notify', 'start_consuming', 'stop_consuming']
    _ask = ['init_consum', 'stop_actor']
    _ref = ['attach']

    def __init__(self, metric_id, routing_key):
        self._observers = {}
        self.value = None
        self.name = None
        self.consumer = None

        self.logstash_host = settings.LOGSTASH_HOST
        self.logstash_port = settings.LOGSTASH_PORT

        self.queue = metric_id
        self.name = metric_id
        self.routing_key = routing_key
        self.logstash_server = (self.logstash_host, self.logstash_port)
        self.metrics = Queue.Queue()

        # Subprocess to aggregate collected metrics every time interval
        self.notifier = Thread(target=self._aggregate_and_send_info)
        self.notifier.start()

        try:
            self.redis = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            logger.info('"Error connecting with Redis DB"')
            print "Error connecting with Redis DB"

    def attach(self, observer):
        """
        Asyncronous method. This method allows to be called remotely. It is
        called from observers in order to subscribe in this workload metric.
        This observer will be saved in a dictionary type structure where the
        key will be the tenant assigned in the observer, and the value will be
        the PyActor proxy to connect to the observer.

        :param observer: The PyActor proxy of the observer rule that calls this method.
        :type observer: **any** PyActor Proxy type
        """

        logger.info('Metric, Attaching observer: ' + str(observer))
        target = observer.get_target(timeout=2)
        observer_id = observer.get_id()

        if target not in self._observers.keys():
            self._observers[target] = dict()
        if observer_id not in self._observers[target].keys():
            self._observers[target][observer_id] = observer

    def detach(self, observer, target):
        """
        Asynchronous method. This method allows to be called remotely.
        It is called from observers in order to unsuscribe from this workload
        metric.

        :param observer: The PyActor actor id of the observer rule that calls this method.
        :type observer: String
        """
        try:
            del self._observers[target][observer]
            if len(self._observers[target]) == 0:
                del self._observers[target]
            logger.info('Metric, observer detached: ' + str(observer))
        except KeyError:
            pass

    def init_consum(self):
        """
        Asynchronous method. This method allows to be called remotely. This
        method registries the workload metric in the redis database. Also
        create a new consumer actor in order to consume from a specific
        rabbitmq queue.

        :raises Exception: Raise an exception when a problem to create the
                           consumer appear.
        """
        try:
            self.redis.hmset("metric:" + self.name, {"network_location": self.proxy.actor.url,
                                                     "type": "integer"})

            self.consumer = self.host.spawn(self.id + "_consumer", settings.CONSUMER_MODULE,
                                            self.queue, self.routing_key, self.proxy)
            self.start_consuming()
        except Exception as e:
            raise ValueError(e.msg)

    def stop_actor(self):
        """
        Asynchronous method. This method allows to be called remotely.
        This method ends the workload execution and kills the actor.
        """
        try:
            # Stop observers
            for tenant in self._observers:
                for observer in self._observers[tenant].values():
                    observer.stop_actor()
                    self.redis.hset(observer.get_id(), 'status', 'Stopped')

            self.redis.delete("metric:" + self.name)
            self.stop_consuming()
            self.host.stop_actor(self.id)

        except Exception as e:
            logger.error(str(e))
            raise e

    def start_consuming(self):
        """
        Start the consumer.
        """
        if self.consumer:
            self.consumer.start_consuming()
        else:
            logger.info('Metric, No consumer available to start')

    def stop_consuming(self):
        """
        Stop the consumer.
        """
        if self.consumer:
            self.consumer.stop_consuming()
        else:
            logger.info('Metric, No consumer available to stop')

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
            metric_list = list()

            while not self.metrics.empty():
                metric = self.metrics.get()
                metric_list.append(metric)
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

                if "ALL" in self._observers and len(metric_list) > 0:
                    for observer in self._observers["ALL"].values():
                        observer.update(self.name, metric_list)

            except Exception as e:
                logger.info("Swift Metric: Error sending monitoring data to observer: "+str(e))
