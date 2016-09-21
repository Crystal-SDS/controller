import redis
import ConfigParser
import sys


class Metric(object):
    """
    Metric: This is an abstract class. This class is the responsible to consume
    messages from rabbitMQ and send the data to each observer subscribed to it.
    This class also treats each tenant as a topic, so it is able to distinguish
    for each observer in that tenant is subscribed. In this way, the metric
    actor only sends the necessary information to each observer.
    """
    def __init__(self):
        self._observers = {}
        self.value = None
        self.name = None
        settings = ConfigParser.ConfigParser()
        settings.read("registry/dynamic_policies/settings.conf")
        self.rmq_user = settings.get('rabbitmq', 'username')
        self.rmq_pass = settings.get('rabbitmq', 'password')
        self.rmq_host = settings.get('rabbitmq', 'host')
        self.rmq_port = settings.get('rabbitmq', 'port')
        self.redis_host = settings.get('redis', 'host')
        self.redis_port = settings.get('redis', 'port')
        self.redis_db = settings.get('redis', 'db')
        self.logstash_host = settings.get('logstash', 'host')
        self.logstash_port = int(settings.get('logstash', 'port'))

        self.redis = redis.StrictRedis(host=self.redis_host,
                                       port=int(self.redis_port),
                                       db=int(self.redis_db))

    def attach(self, observer):
        """
        Asyncronous method. This method allows to be called remotelly. It is
        called from observers in order to subscribe in this workload metric.
        This observer will be saved in a dictionary type structure where the
        key will be the tenant assigned in the observer, and the value will be
        the PyActive proxy to connect to the observer.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        # TODO: Add the possibility to subscribe to container or object
        print ' - Metric, Attaching observer: ', observer
        tenant = observer.get_target()

        if tenant not in self._observers.keys():
            self._observers[tenant] = set()
        if observer not in self._observers[tenant]:
            self._observers[tenant].add(observer)

    def detach(self, observer, target):
        """
        Asyncronous method. This method allows to be called remotelly.
        It is called from observers in order to unsubscribe from this workload
        metric.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        print ' - Metric, Detaching observer: ', observer
        try:
            self._observers[target].remove(observer)
        except KeyError:
            pass

    def init_consum(self):
        """
        Asynchronous method. This method allows to be called remotelly. This
        method registries the workload metric in the redis database. Also
        create a new consumer actor in order to consume from a specific
        rabbitmq queue.

        :raises Exception: Raise an exception when a problem to create the
                           consumer appear.
        """
        try:
            print '- Starting consumer'
            self.redis.hmset("metric:"+self.name, {"network_location": self._atom.aref.replace("atom:", "tcp:", 1), "type": "integer"})

            self.consumer = self.host.spawn_id(self.id + "_consumer",
                                               "registry.dynamic_policies.consumer",
                                               "Consumer",
                                               [str(self.rmq_host),
                                                int(self.rmq_port),
                                                str(self.rmq_user),
                                                str(self.rmq_pass),
                                                self.exchange,
                                                self.queue,
                                                self.routing_key,
                                                self.proxy])
            self.start_consuming()
        except:
            e = sys.exc_info()[0]
            print e

    def stop_actor(self):
        """
        Asynchronous method. This method allows to be called remotelly.
        This method ends the workload execution and kills the actor.
        """
        try:
            # Stop observers
            for tenant in self._observers:
                for observer in self._observers[tenant]:
                    observer.stop_actor()
                    self.redis.hset(observer.get_id(), 'alive', 'False')

            self.redis.delete("metric:"+self.name)
            self.stop_consuming()
            self._atom.stop()

        except Exception as e:
            print e

    def start_consuming(self):
        """
        Start the consumer.
        """
        self.consumer.start_consuming()

    def stop_consuming(self):
        """
        Stop the consumer.
        """
        self.consumer.stop_consuming()
