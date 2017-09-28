from redis.exceptions import RedisError
from django.conf import settings
import logging
import Queue
import pika
import redis

logger = logging.getLogger(__name__)


class AbstractController(object):

    _ask = ['get_target']
    _tell = ['update', 'run', 'stop_actor', 'notify']

    metrics = []

    def __init__(self):
        self.rmq_user = settings.RABBITMQ_USERNAME
        self.rmq_pass = settings.RABBITMQ_PASSWORD
        self.rmq_host = settings.RABBITMQ_HOST
        self.rmq_port = settings.RABBITMQ_PORT
        self.rmq_exchange = settings.RABBITMQ_EXCHANGE

        self.rmq_credentials = pika.PlainCredentials(self.rmq_user,
                                                     self.rmq_pass)

        try:
            self.redis = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            logger.info('"Error connecting with Redis DB"')

        self.metric_data = Queue.Queue()
        self.rmq_messages = Queue.Queue()

    def _subscribe_metrics(self):
        for metric in self.metrics:
            metric_actor = self.host.lookup(metric)
            metric_actor.attach(self.proxy)

    def _connect_rmq(self):
        parameters = pika.ConnectionParameters(host=self.rmq_host,
                                               credentials=self.rmq_credentials)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()

    def _disconnect_rmq(self):
        try:
            self._channel.close()
            self._connection.close()
        except:
            pass

    def _send_message_rmq(self, routing_key, message):
        self._channel.basic_publish(exchange=self.rmq_exchange,
                                    routing_key=routing_key,
                                    body=str(message))

    def _init_consum(self, queue, routing_key):
        try:
            self.consumer = self.host.spawn(self.id + "_consumer", settings.CONSUMER_MODULE,
                                            [self.queue, self.routing_key, self.proxy])
            self.start_consuming()
        except Exception as e:
            print e

    def notify(self, body):
        """
        Method called from the consumer to indicate the value consumed from the
        rabbitmq queue. After receive the value, this value is communicated to
        all the observers subscribed to this metric.
        """
        self.rmq_messages.put(body)

    def get_target(self):
        """
        This controller will be subscribed to all Projects
        """
        return "ALL"

    def update(self, metric_name, metric_data):
        """
        Method called from the Swift Metric to indicate the new metric dada
        """
        self.compute_data(metric_data)

    def run(self):
        """
        Entry Method
        """
        self._subscribe_metrics()
        self._connect_rmq()

    def stop_actor(self):
        """
        Asynchronous method. This method can be called remotely.
        This method ends the controller execution and kills the actor.
        """
        try:
            if self.metrics:
                for metric in self.metrics:
                    metric_actor = self.host.lookup(metric)
                    metric_actor.detach(self.proxy, self.get_target())
            self._disconnect_rmq()
            self.host.stop_actor(self.id)
        except Exception as e:
            logger.error(str(e.message))
