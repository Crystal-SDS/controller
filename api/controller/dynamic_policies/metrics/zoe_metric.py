import json
from abstract_metric import Metric


class ZoeMetric(Metric):
    _tell = ['attach', 'detach', 'notify', 'start_consuming', 'stop_consuming', 'init_consum', 'stop_actor']
    _ref = ['attach', 'detach']

    def __init__(self, name, exchange, queue, routing_key):
        Metric.__init__(self)

        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.name = name

    def notify(self, body):
        """
        Method called from the consumer to indicate the value consumed from the
        rabbitmq queue. After receiving the value, this value is communicated to
        all the observers subscribed to this metric.

        e.g.:
            tenant1:gold
        """

        print "Zoe Metric - message received: " + body

        received_data = body.split(':')
        zoe_data = {"tenant": received_data[0], "abstract_policy": received_data[1].lower()}

        try:
            for observer in self._observers:
                observer.update(self.name, None, json.dumps(zoe_data))

        except Exception as e:
            print "Fail sending monitoring data to observer: ", e

    def attach(self, observer):
        """
        Asynchronous method. This method allows to be called remotely. It is
        called from observers in order to subscribe to this workload metric.
        This observer (the PyActive proxy) will be saved in a set structure.

        :param observer: The PyActive proxy of the observer that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        print('Zoe Metric, Attaching observer: ' + str(observer))
        # tenant = observer.get_target()

        if not self._observers:
            self._observers = set()
        if observer not in self._observers:
            self._observers.add(observer)

    def stop_actor(self):
        """
        Asynchronous method. This method allows to be called remotely.
        This method ends the workload execution and kills the actor.
        """
        try:
            self.redis.delete("metric:" + self.name)
            self.stop_consuming()
            self.host.stop_actor(self.id)

        except Exception as e:
            print e