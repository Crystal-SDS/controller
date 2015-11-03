from abstract_metric import Metric


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


    def get_value(self):
        return self.value
