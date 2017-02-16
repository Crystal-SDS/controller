import datetime
import logging

import pika
import redis
from redis.exceptions import RedisError

# from api.settings import RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, REDIS_CON_POOL
from django.conf import settings

# logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class AbstractEnforcementAlgorithm(object):
    """
    This is an abstract class. This class is the responsible to
    i) obtain goal assignments from Redis,
    ii) subscribe to a relevant metric actor,
    iii) send computed assignments to a global filter via RabbitMQ.
    
    Global controller algorithms (e.g.: Bandwidth controllers) must extend this class and implement the compute_algorithm method.
    """
    _sync = {'get_tenant': '2'}
    _async = ['update', 'run', 'stop_actor']
    _ref = []
    _parallel = []

    def __init__(self, name, method):
        """
        """
        # settings = ConfigParser.ConfigParser()
        # config_file = (os.path.join(os.getcwd(), 'controller', 'dynamic_policies', 'settings.conf'))
        # settings.read(config_file)

        logging.info('Rule init: OK')
        self.rmq_user = settings.RABBITMQ_USERNAME
        self.rmq_pass = settings.RABBITMQ_PASSWORD
        self.rmq_host = settings.RABBITMQ_HOST
        self.rmq_port = settings.RABBITMQ_PORT
        self.rmq_exchange = 'bw_assignations'  # RABBITMQ_EXCHANGE

        self.credentials = pika.PlainCredentials(self.rmq_user, self.rmq_pass)

        try:
            self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        except RedisError:
            logger.info('"Error connecting with Redis DB"')
            print "Error connecting with Redis DB"

        self.last_bw = dict()
        self.last_update = datetime.datetime.now()
        self.name = name
        self.method = method
        self.workload_metric_id = ''

    def run(self, workload_metric_id):
        """
        The `run()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_metric_id: The name that identifies the workload metric.
        :type workload_metric_id: **any** String type

        """
        try:
            self.workload_metric_id = workload_metric_id
            metric_actor = self.host.lookup(workload_metric_id)
            metric_actor.attach(self.proxy, True)
        except Exception as e:
            raise Exception('Error attaching to metric bw_info: ' + str(e))

    def connect_rmq(self):
        # TODO: WARNING: BlockingConnection can block the actor
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.rmq_host, credentials=self.credentials))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=self.rmq_exchange, exchange_type='topic')

    def disconnect_rmq(self):
        self._channel.close()
        self._connection.close()

    def send_message_rmq(self, message, routing_key):
        self.connect_rmq()
        self._channel.basic_publish(exchange=self.rmq_exchange, routing_key=routing_key, body=str(message))
        # self.disconnect_rmq()

    def update(self, metric, info):
        results = self.compute_algorithm(info)

        now = datetime.datetime.now()
        difference = (now - self.last_update).total_seconds()
        if difference >= 5:
            self.last_bw = dict()

        self.send_results(results)
        self.last_bw = results
        self.last_update = now

    def compute_algorithm(self, info):
        """
        Returns a NotImplemented Exception.
        This method must be implemented by subclasses.
        """
        return NotImplemented

    # def _get_redis_bw(self):
    #     """
    #     Gets the bw assignation from the redis database
    #     """
    #     bw = dict()
    #     keys = self.r.keys("bw:*")
    #     for key in keys:
    #         bw[key[3:]] = self.r.hgetall(key)
    #     return bw

    def send_results(self, assign):
        """
        Sends the calculated BW to each Node that has active requests
        """
        for account in assign:
            for ip in assign[account]:
                new_flow = account not in self.last_bw or ip not in self.last_bw[account]
                if self.last_bw and not new_flow and int(assign[account][ip]) == int(self.last_bw[account][ip]):
                    continue
                node_ip = ip.split('-')
                address = node_ip[0] + '/' + account + '/' + self.method + '/' + node_ip[1] + '/' + node_ip[2] + '/' + str(round(assign[account][ip], 1))
                routing_key = '#.' + node_ip[0] + ".#"
                print "BW CHANGED: " + str(address)
                self.send_message_rmq(address, routing_key)

    def get_tenant(self):
        """
        Returns the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant

    def stop_actor(self):
        """
        Asynchronous method. This method can be called remotely.
        This method ends the controller execution and kills the actor.
        """
        try:
            if self.workload_metric_id:
                metric_actor = self.host.lookup(self.workload_metric_id)
                metric_actor.detach_global_obs()

            self._atom.stop()

        except Exception as e:
            logger.error(str(e))
            print e
