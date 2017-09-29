from django.conf import settings
from threading import Thread
import logging
import pika

logging.getLogger("pika").propagate = False
logger = logging.getLogger(__name__)


class Consumer(object):
    _tell = ['start_consuming', 'stop_consuming']

    def __init__(self, queue, routing_key, parent):

        rmq_user = settings.RABBITMQ_USERNAME
        rmq_pass = settings.RABBITMQ_PASSWORD
        rmq_host = settings.RABBITMQ_HOST
        rmq_port = settings.RABBITMQ_PORT
        exchange = settings.RABBITMQ_EXCHANGE

        credentials = pika.PlainCredentials(rmq_user, rmq_pass)
        parameters = pika.ConnectionParameters(host=rmq_host,
                                               port=rmq_port,
                                               credentials=credentials)
        self._channel = pika.BlockingConnection(parameters).channel()

        self.parent = parent
        self.queue = queue
        self.routing_key = routing_key

        self._channel.queue_declare(queue=queue)

        if routing_key:
            self._channel.queue_bind(exchange=exchange,
                                     queue=queue,
                                     routing_key=routing_key)
            self.consumer = self._channel.basic_consume(self.callback,
                                                        queue=queue,
                                                        no_ack=True)
        else:
            logger.error("Consumer: You must entry a routing key")
            print "You must entry a routing key"

    def callback(self, ch, method, properties, body):
        self.parent.notify(body)

    def start_consuming(self):
        logger.info('Start to consume from RabbitMQ: '+self.routing_key)
        self.thread = Thread(target=self._channel.start_consuming)
        self.thread.start()

    def stop_consuming(self):
        logger.info('Stopping to consume from RabbitMQ: '+self.routing_key)
        self.host.stop_actor(self.id)
        self._channel.stop_consuming()
        self._channel.close()
