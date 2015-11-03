from abstract_metric import Metric

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
