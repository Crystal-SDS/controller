import pika
import logging
import json
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError

class Metric(object):

    def __init__(self):
        self._observers = {}
        self.value = None
        self.name = None

    def attach(self, observer):
        tenant = observer.get_tenant()
        if not tenant in self._observers.keys():
            self._observers[tenant] = set()
        if not observer in self._observers[tenant]:
            self._observers[tenant].add(observer)

    def detach(self, observer):
        tenant = observer.get_tenant()
        try:
            self._observers[tenant].remove(observer)
        except KeyError:
            pass

    def init_consum(self):
        self.consumer = self.host.spawn_id(self.id + "_consumer", "metric", "Consumer", ["localhost", 25672, self.queue, self.proxy])
        self.start_consuming()

    def start_consuming(self):
        self.consumer.start_consuming()

    def stop_consuming(self):
        self.consumer.stop_consuming()

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
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, queue, host):
        Metric.__init__(self)
        # Queue name should be take from config file
        self.host = host

        self.queue = queue
        print 'Througput initialized'
        self.name = "througput"
        # Consumer("localhost", 25672, queue, self)
        # thread1 = Consumer("localhost", 25672, queue, self)
        # Start new Threads
        # thread1.start()

    def get_value(self):
        return self.value
    #
    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)

class Slowdown(Metric):
    _sync = {}
    _async = ['get_value', 'attach', 'detach', 'notify', 'start_consuming','stop_consuming', 'init_consum']
    _ref = ['attach', 'detach']
    _parallel = []

    def __init__(self, queue, host):
        Metric.__init__(self)

        self.host = host
        self.queue = queue
        self.name = "slowdown"
        # Consumer("localhost", 25672, queue, self)
        # thread1 = Consumer("localhost", 25672, queue, self)
        # Start new Threads
        # thread1.start()
        print 'Slowdown initialized'

    def get_value(self):
        return self.value

    # def callback(self, ch, method, properties, body):
    #     print 'body', body
    #     self.notify(body)

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
