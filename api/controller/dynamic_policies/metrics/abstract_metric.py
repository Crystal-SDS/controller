from django.conf import settings
from redis.exceptions import RedisError
import logging
import redis

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
        self.consumer = None

        self.rmq_user = settings.RABBITMQ_USERNAME
        self.rmq_pass = settings.RABBITMQ_PASSWORD
        self.rmq_host = settings.RABBITMQ_HOST
        self.rmq_port = settings.RABBITMQ_PORT

        self.logstash_host = settings.LOGSTASH_HOST
        self.logstash_port = settings.LOGSTASH_PORT

        try:
            self.redis = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            logger.info('"Error connecting with Redis DB"')
            print "Error connecting with Redis DB"

    def attach(self, observer):
        """
        Asyncronous method. This method allows to be called remotely. It is
        called from observers in order to subscribe in this workload metric.
        This observer will be saved in a dictionary type structure where the
        key will be the tenant assigned in the observer, and the value will be
        the PyActor proxy to connect to the observer.

        :param observer: The PyActor proxy of the oberver rule that calls this method.
        :type observer: **any** PyActor Proxy type
        """

        logger.info('Metric, Attaching observer: ' + str(observer))
        target = observer.get_target(timeout=2)
        logger.info('Metric, target is: ' + str(target))
        observer_id = observer.get_id()

        if target not in self._observers.keys():
            self._observers[target] = dict()
        if observer_id not in self._observers[target].keys():
            self._observers[target][observer_id] = observer
        logger.info('Metric, _observers keys are: ' + str(self._observers.keys()))

    def detach(self, observer, target):
        """
        Asynchronous method. This method allows to be called remotely.
        It is called from observers in order to unsubscribe from this workload
        metric.

        :param observer: The PyActor actor id of the oberver rule that calls this method.
        :type observer: String
        """
        logger.info('Metric, Detaching observer: ' + str(observer))
        try:
            del self._observers[target][observer]
        except KeyError:
            pass

    def init_consum(self):
        """
        Asynchronous method. This method allows to be called remotely. This
        method registries the workload metric in the redis database. Also
        create a new consumer actor in order to consume from a specific
        rabbitmq queue.

        :raises Exception: Raise an exception when a problem to create the
                           consumer appear.
        """
        try:
            self.redis.hmset("metric:" + self.name, {"network_location": self.proxy.actor.url,
                                                     "type": "integer"})

            self.consumer = self.host.spawn(self.id + "_consumer",
                                            "controller.dynamic_policies.metrics.consumer" +
                                            "/Consumer",
                                            [str(self.rmq_host),
                                             int(self.rmq_port),
                                             str(self.rmq_user),
                                             str(self.rmq_pass),
                                             self.exchange,
                                             self.queue,
                                             self.routing_key,
                                             self.proxy])
            self.start_consuming()
        except Exception, e:
            print e

    def stop_actor(self):
        """
        Asynchronous method. This method allows to be called remotely.
        This method ends the workload execution and kills the actor.
        """
        try:
            # Stop observers
            for tenant in self._observers:
                for observer in self._observers[tenant].values():
                    observer.stop_actor()
                    self.redis.hset(observer.get_id(), 'alive', 'False')

            self.redis.delete("metric:" + self.name)
            self.stop_consuming()
            self.host.stop_actor(self.id)

        except Exception as e:
            logger.error(str(e))
            print e

    def start_consuming(self):
        """
        Start the consumer.
        """
        if self.consumer:
            self.consumer.start_consuming()
        else:
            logger.info('Metric, No consumer available to start')

    def stop_consuming(self):
        """
        Stop the consumer.
        """
        if self.consumer:
            self.consumer.stop_consuming()
        else:
            logger.info('Metric, No consumer available to stop')
