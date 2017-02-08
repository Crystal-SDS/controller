import sys
import logging
import redis

#from api.settings import RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, REDIS_CON_POOL, LOGSTASH_HOST, LOGSTASH_PORT
from django.conf import settings
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)


class Metric(object):
    """
    Metric: This is an abstract class. This class is the responsible to consume
    messages from RabbitMQ and send the data to each observer subscribed to it.
    This class also treats each tenant as a topic, so it is able to distinguish
    for each observer in that tenant is subscribed. In this way, the metric
    actor only sends the necessary information to each observer.
    """

    def __init__(self):
        self._observers = {}
        self.value = None
        self.name = None
        # settings = ConfigParser.ConfigParser()
        # settings.read("registry/dynamic_policies/settings.conf")
        self.rmq_user = settings.RABBITMQ_USERNAME
        self.rmq_pass = settings.RABBITMQ_PASSWORD
        self.rmq_host = settings.RABBITMQ_HOST
        self.rmq_port = settings.RABBITMQ_PORT
        # self.redis_host = REDIS_HOST
        # self.redis_port = REDIS_PORT
        # self.redis_db = REDIS_DATABASE
        self.logstash_host = settings.LOGSTASH_HOST
        self.logstash_port = settings.LOGSTASH_PORT

        # self.redis = redis.StrictRedis(host=self.redis_host,
        #                                port=int(self.redis_port),
        #                                db=int(self.redis_db))

        try:
            self.redis = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            logger.info('"Error connecting with Redis DB"')
            print "Error connecting with Redis DB"

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
        logger.info('Metric, Attaching observer: ' + observer)
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
        logger.info('Metric, Detaching observer: ' + observer)
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
            self.redis.hmset("metric:" + self.name, {"network_location": self._atom.aref.replace("atom:", "tcp:", 1), "type": "integer"})

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

            self.redis.delete("metric:" + self.name)
            self.stop_consuming()
            self._atom.stop()

        except Exception as e:
            logger.error(str(e))
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
