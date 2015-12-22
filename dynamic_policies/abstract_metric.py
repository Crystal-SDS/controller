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
        print 'attach new observer', observer
        tenant = observer.get_tenant()
        print 'observer tenant', tenant
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
        try:

            r = redis.StrictRedis(host=self.redis_host, port=int(self.redis_port), db=int(self.redis_db))
            r.hmset("metric:"+self.name, {"network_location":self._atom.aref.replace("atom:", "tcp:", 1), "type":"integer"})
            self.consumer = self.host.spawn_id(self.id + "_consumer", "consumer", "Consumer", [str(self.rmq_host), int(self.rmq_port), str(self.rmq_user), str(self.rmq_pass), self.exchange, self.queue, self.routing_key, self.proxy])

            self.start_consuming()
        except:
            raise Exception("Problems to connect to RabbitMQ server")


    def stop_actor(self):
        self.consumer.stop_consuming()
        self._atom.stop()

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
