import pika
import logging
from threading import Thread

logging.basicConfig()


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

        print '- Exchange:', exchange
        # result = channel.queue_declare(exclusive=True)
        self._channel.queue_declare(queue=queue)
        # queue_name = result.method.queue
        print '- Routing_key: ', routing_key

        if routing_key:
            self._channel.queue_bind(exchange=exchange,
                                     queue=queue,
                                     routing_key=routing_key)
            self.consumer = self._channel.basic_consume(self.callback,
                                                        queue=queue,
                                                        no_ack=True)
        else:
            print "You must entry a routing key"

    def callback(self, ch, method, properties, body):
        self.obj.notify(body)

    def start_consuming(self):
        print '- Start to consume from rabbitmq'
        self.thread = Thread(target=self._channel.start_consuming)
        self.thread.start()

    def stop_consuming(self):
        self._channel.stop_consuming()
        self._channel.close()
        self._atom.stop()
