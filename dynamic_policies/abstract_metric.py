import json
import redis
import ConfigParser

class Metric(object):
    """
    Metric: This is an abstract class. This class is the responsible to consume messages
    from rabbitMQ and send the data to each observer subscribed to it. This class also
    treats each tenant as a topic, so it is able to distinguish for each observer in
    that tenant is subscribed. In this way, the metric actor only sends the necessary
    information to each observer.
    """
    def __init__(self):
        self._observers = {}
        self.value = None
        self.name = None
        settings = ConfigParser.ConfigParser()
        settings.read("./dynamic_policies.config")
	
        self.rmq_user =  settings.get('rabbitmq', 'username')
        self.rmq_pass = settings.get('rabbitmq', 'password')
        self.rmq_host = settings.get('rabbitmq', 'host')
        self.rmq_port = settings.get('rabbitmq', 'port')
        self.redis_host = settings.get('redis', 'host')
        self.redis_port = settings.get('redis', 'port')
        self.redis_db = settings.get('redis', 'db')

    def attach(self, observer):
        """
        Asyncronous method. This method allows to be called remotelly. It is called from
        observers in order to subscribe in this workload metric. This observer will be
        saved in a dictionary type structure where the key will be the tenant assigned in the observer,
        and the value will be the PyActive proxy to connect to the observer.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        #TODO: Add the possibility to subscribe to container or object
	print 'attach', observer
        tenant = observer.get_target()

        if not tenant in self._observers.keys():
            self._observers[tenant] = set()
        if not observer in self._observers[tenant]:
            self._observers[tenant].add(observer)

    def detach(self, observer):
        """
        Asyncronous method. This method allows to be called remotelly. It is called from
        observers in order to unsubscribe from this workload metric.

        :param observer: The PyActive proxy of the oberver rule that calls this method.
        :type observer: **any** PyActive Proxy type
        """
        tenant = observer.get_target()
        try:
            self._observers[tenant].remove(observer)
        except KeyError:
            pass

    def init_consum(self):
        """
        Asynchronous method. This method allows to be called remotelly. This method registries the workload
        metric in the redis database. Also create a new consumer actor in order to consume from a specific
        rabbitmq queue.

        :raises Exception: Raise an exception when a problem to create the consumer appear.
        """
        # try:
	print 'start_consume'
        r = redis.StrictRedis(host=self.redis_host, port=int(self.redis_port), db=int(self.redis_db))
        r.hmset("metric:"+self.name, {"network_location":self._atom.aref.replace("atom:", "mom:", 1), "type":"integer"})
        print 'before consumer'
        self.consumer = self.host.spawn_id(self.id + "_consumer", "consumer", "Consumer", [str(self.rmq_host), int(self.rmq_port), str(self.rmq_user), str(self.rmq_pass), self.exchange, self.queue, self.routing_key, self.proxy])
        self.start_consuming()
        # except:
        #     raise Exception("Problems to connect to RabbitMQ server")


    def stop_actor(self):
        """
        Asynchronous method. This method allows to be called remotelly. This method ends the workload execution and
        kills the actor.
        """
        self.consumer.stop_consuming()
        self._atom.stop()

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

    def notify(self, body):
        """
        Method called from the consumer to indicate the value consumed from the rabbitmq queue. After receive the value,
        this value is communicated to all the observers subscribed to this metric.
        """
        data = json.loads(body)
        for tenant_info in data:
            try:
                for observer in self._observers[tenant_info["tenant_id"]]:
                    observer.update(self.name, tenant_info)
            except:
                #print "fail", tenant_info
                pass
