from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import operator
import json
import redis
import pika
import logging

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

#TODO: Add the redis connection into rule object
r = redis.StrictRedis(host='localhost', port=6379, db=0)
logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class RuleBw(Rule):
    """
    Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
    in the workloads metrics. When the data received from the workloads metrics satisfies
    the conditions defined in the policy,the Rule actor executes an Action that it is
    also defined in the policy.
    """
    _sync = {'get_tenant':'2'}
    _async = ['update', 'start_rule', 'stop_actor', 'add_metric']
    _ref = []
    _parallel = []

    def __init__(self, rule_parsed, target):
        """
        Inicialize all the variables needed for the rule.

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param tenant: The tenant id assigned to this rule.
        :type tenant_info: **any** String type
        :param host: The proxy host provided by the PyActive Middleware.
        :type host: **any** PyActive Proxy type
        :param host_ip: The host ip adress.
        :type host_ip: **any** String type
        :param host_port: The host port address.
        :type host_port: **any** Numeric type.
        :param host_transport: The host transport used for the comunication.
        :type host_transport: **any** String type.

        """
        logging.info('Rule init: OK')
        #TODO take this parameters from configuration
        self.redis_host='84.88.51.222'
        self.redis_port=6379
        self.rmq_user =  'guest'
        self.rmq_pass = 'guest'
        self.rmq_host = '84.88.51.222'
        self.rmq_port = 5672
        self.rmq_exchange = 'bw_assignations'
        self.credentials = pika.PlainCredentials(self.rmq_user, self.rmq_pass)
        try:
            self.r = redis.Redis(connection_pool=redis.ConnectionPool(host=self.redis_host, port=self.redis_port, db=0))
        except:
            return Response('Error connecting with DB', status=500)
        self.last_bw = self.load_last_bw()

        super(RuleBw, self).__init__(rule_parsed, target)

    def add_metric(self, workload_name):
        """
        The `add_metric()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        try:
            observer = self.host.lookup(workload_name)
            observer.attach(self.proxy, True)
        except:
            raise Exception('Error attaching to metric get_bw_info')

    def load_last_bw(self):
        last = dict()
        keys = self.r.keys("last_bw:*")
        for key in keys:
            last[key[8:]] = self.r.hgetall(key)
        return last

    def connect_rmq(self):
        #TODO: WARNING: BlockingConnection can block the actor
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.redis_host, credentials=self.credentials))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=self.rmq_exchange,
                             exchange_type='topic')

    def disconnect_rmq(self):
        self._channel.close()
        self._connection.close()

    def send_message_rmq(self, message, routing_key):
        self.connect_rmq()
        self._channel.basic_publish(exchange=self.rmq_exchange,routing_key=routing_key, body=str(message))
        self.disconnect_rmq()

    def update(self, metric, info):
        self.info = info
        self.assignations = self.compute_assignations(info)
        self.send_bw(self.assignations)

    def compute_assignations(self, info):
        """
        BW assignation algorithm
        :return: dict[account][policy]['ips'][ip]:bw
        """
        assign = dict()
        bw_a = dict()
        bw = self.get_redis_bw()
        for account in info:
            assign[account] = dict()
            bw_a[account] = dict()
            for ip in info[account]:
                for policy in info[account][ip]:
                    if not policy in assign[account]:
                        assign[account][policy] = dict()
                    if not 'num' in assign[account][policy]:
                        assign[account][policy]['num'] = 1
                    else:
                        assign[account][policy]['num'] += 1
                    if not 'ips' in assign[account][policy]:
                        assign[account][policy]['ips'] = set()
                    assign[account][policy]['ips'].add(ip)

            for policy in assign[account]:
                for ip in assign[account][policy]['ips']:
                    try:
                        bw_a[account][ip+"-"+policy] = int(bw[account][policy])/assign[account][policy]['num']
                    except:
                        bw_a[account][ip+"-"+policy] = -1

        return bw_a


    def get_redis_bw(self):
        """
        Gets the bw assignation from the redis database
        """
        bw = dict()
        keys = self.r.keys("bw:*")
        for key in keys:
            bw[key[3:]] = self.r.hgetall(key)
        return bw

    def send_bw(self, assign):
        routing_key = "."
        address = " "
        send = False
        for account in assign:
            for ip in assign[account]:

                if account in self.last_bw and ip in self.last_bw[account]:
                    if int(assign[account][ip]) != int(self.last_bw[account][ip]):
                        send = True
                        ip_c = ip.split('-')
                        address = address + ip_c[0]+'/'+account+'/'+ ip_c[1]+'/'+str(assign[account][ip])+'/ '
                        routing_key = routing_key + ip_c[0].replace('.','-').replace(':','-') + "."
                        self.r.hset("last_bw:"+account, ip, assign[account][ip])
                        self.last_bw[account][ip] = assign[account][ip]
                else:
                    send = True
                    ip_c = ip.split('-')
                    address = address + ip_c[0]+'/'+account+'/'+ ip_c[1]+'/'+str(assign[account][ip])+'/ '
                    routing_key = routing_key + ip_c[0].replace('.','-').replace(':','-') + "."
                    self.r.hset("last_bw:"+account, ip, assign[account][ip])
                    if not account in self.last_bw:
                        self.last_bw[account] = dict()
                    self.last_bw[account][ip] = assign[account][ip]
        if send:
            print "BW CHANGED"
            self.send_message_rmq(address, routing_key)
            print address

    def get_tenant(self):
        """
        Return the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant
