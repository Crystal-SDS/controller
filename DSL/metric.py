import pika
import logging
import json
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
class Metric():

    def __init__(self):
        self._observers = {}
        self.value = None
        self.name = None
        # host should be obtained from config file like queue names
        # self.channel = pika.BlockingConnection(pika.ConnectionParameters(
        #     host='localhost', port=25672)).channel()

    def attach(self, observer):
        print "observer", observer.tenant
        if not observer.tenant in self._observers.keys():
            self._observers[observer.tenant] = set()
        if not observer in self._observers[observer.tenant]:
            self._observers[observer.tenant].add(observer)

    def detach(self, observer):
        try:
            self._observers[observer.tenant].remove(observer)
        except KeyError:
            pass

    def notify(self, body):
        data = json.loads(body)
        for tenant_info in data:
            try:
                for observer in self._observers[tenant_info["tenant_id"]]:
                    observer.update(self.name, tenant_info)
            except:
                print "fail", tenant_info
                pass

class Througput(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach']
    _ref = []
    _parallel = []

    def __init__(self, queue):
        Metric.__init__(self)
        # Queue name should be take from config file
        self.channel = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=25672)).channel()
        self.channel.queue_declare(queue=queue)
        self.channel.basic_consume(self.callback,
                              queue=queue,
                              no_ack=True)
        self.thread = Thread(target=self.start_consuming)
        self.thread.start()

        self.name = "througput"
        # Consumer("localhost", 25672, queue, self)
        # thread1 = Consumer("localhost", 25672, queue, self)
        # Start new Threads
        # thread1.start()

    def get_value(self):
        return self.value

    def start_consuming(self):
        self.channel.start_consuming()

    def stop_consuming(self):
        self.channel.stop_consuming()
        self.channel.close()

    def callback(self, ch, method, properties, body):
        print 'body', body
        self.notify(body)

class Slowdown(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach']
    _ref = []
    _parallel = []

    def __init__(self, queue):
        Metric.__init__(self)
        # Queue name should be take from config file
        self.channel = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=25672)).channel()
        self.channel.queue_declare(queue=queue)
        self.channel.basic_consume(self.callback,
                              queue=queue,
                              no_ack=True)
        self.thread = Thread(target=self.start_consuming)
        self.thread.start()

        self.name = "slowdown"
        # Consumer("localhost", 25672, queue, self)
        # thread1 = Consumer("localhost", 25672, queue, self)
        # Start new Threads
        # thread1.start()

    def get_value(self):
        return self.value

    def start_consuming(self):
        self.channel.start_consuming()

    def stop_consuming(self):
        self.channel.stop_consuming()
        self.channel.close()

    def callback(self, ch, method, properties, body):
        print 'body', body
        self.notify(body)

class Consumer (Thread):
    def __init__(self, host, port, queue, obj):
        threading.Thread.__init__(self)

        self._consumer_tag
        self._channel = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=25672)).channel()
        self.obj = obj
        self.queue = queue
        self._channel.queue_declare(queue=queue)
        # self.consumer = self.channel.basic_consume(self.callback,
        #                       queue=queue,
        #                       no_ack=True)

    def run(self):
        self.start_consume()


    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.
        """

        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.callback,
                              queue=self.queue,
                              no_ack=True)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.

        """
        if self._channel:
            LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        LOGGER.info('Closing the channel')
        self._channel.close()

    def callback(self, ch, method, properties, body):
        print 'body', body
        self.obj.notify(body)
