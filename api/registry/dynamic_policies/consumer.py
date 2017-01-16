from threading import Thread
import logging
import pika

logger = logging.getLogger(__name__)


class Consumer(object):
    _sync = {}
    _async = ['start_consuming', 'stop_consuming']
    _ref = []
    _parallel = []

    def __init__(self, host, port, username, password, exchange, queue, routing_key, obj):

        credentials = pika.PlainCredentials(username, password)
        parameters = pika.ConnectionParameters(host=host,
                                               port=port,
                                               credentials=credentials)
        self._channel = pika.BlockingConnection(parameters).channel()

        self.obj = obj
        self.queue = queue

        logger.info('Metric, Exchange:' + exchange)
        logger.info('Metric, Routing_key: ' + routing_key)

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
        self.obj.notify(body)

    def start_consuming(self):
        logger.info('Metric, Start to consume from rabbitmq')
        self.thread = Thread(target=self._channel.start_consuming)
        self.thread.start()

    def stop_consuming(self):
        logger.info('Metric, Stopping to consume from rabbitmq')
        self._atom.stop()
        self._channel.stop_consuming()
        self._channel.close()
