import pika

class Consumer(object):
    _sync = {}
    _async = ['start_consuming', 'stop_consuming']
    _ref = []
    _parallel = []

    def __init__(self, host, port, queue, obj):
        self._channel = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=25672)).channel()
        self.obj = obj
        self.queue = queue
        self._channel.queue_declare(queue=queue)
        self.consumer = self._channel.basic_consume(self.callback,
                                        queue=queue,
                                        no_ack=True)
        print 'consumer initialized'
    def callback(self, ch, method, properties, body):
        self.obj.notify(body)

    def start_consuming(self):
        print 'start to consume!!! :D'
        self._channel.start_consuming()

    def stop_consuming(self):
        self._channel.stop_consuming()
        self._channel.close()
