from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import operator
import json
import redis
import pika
import logging
import syslog
import ConfigParser

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

#TODO: Add the redis connection into rule object
r = redis.StrictRedis(host='localhost', port=6379, db=0)
logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class AbstractEnforcementAlgorithm(object):
    """
    TODO: Review the documentation of this class

    AbstractEnforcementAlgorithm:
    """
    _sync = {'get_tenant':'2'}
    _async = ['update', 'start_rule', 'run', 'add_metric']
    _ref = []
    _parallel = []

    def __init__(self, name):
        """
        """
	settings = ConfigParser.ConfigParser() 
	settings.read("./dynamic_policies.config")

        logging.info('Rule init: OK')
        self.rmq_user = settings.get('rabbitmq', 'username')
        self.rmq_pass = settings.get('rabbitmq', 'password')
        self.rmq_host = settings.get('rabbitmq', 'host')
        self.rmq_port = int(settings.get('rabbitmq', 'port'))
        self.redis_host = settings.get('redis', 'host')
        self.redis_port = int(settings.get('redis', 'port'))
        self.redis_db = int(settings.get('redis', 'db'))
        self.rmq_exchange = 'bw_assignations'
        self.credentials = pika.PlainCredentials(self.rmq_user, self.rmq_pass)
        try:
            self.r = redis.Redis(connection_pool=redis.ConnectionPool(host=self.redis_host, port=self.redis_port, db=0))
        except:
            return Response('Error connecting with DB', status=500)
        self.last_bw = dict()
        self.name = name

    def run(self, workload_metic_id):
        """
        The `run()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        try:
            observer = self.host.lookup(workload_metic_id)
            observer.attach(self.proxy, True)
        except Exception as e:
            raise Exception('Error attaching to metric get_bw_info: '+str(e))

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
        #self.disconnect_rmq()

    def update(self, metric, info):
        self.info = info
        results = self.compute_algorithm(info)
        self.send_results(results)
	self.last_bw = results

    def compute_algorithm(self, info):
        """
        return exception unnimplemented method
        """
	return NotImplemented
	'''
        assign = dict()
        bw_a = dict()
        bw = self.get_redis_bw()

	
        for account in info:
            assign[account] = dict()
            bw_a[account] = dict()
            for ip in info[account]:
                for policy in info[account][ip]:
		    for device in info[account][ip][policy]:
                    	if not policy in assign[account]:
                            assign[account][policy] = dict()
			if not device in assign[account][policy]:
			    assign[account][policy][device] = dict()
                    	if not 'requests' in assign[account][policy][device]:
                            assign[account][policy][device]['requests'] = 1
                    	else:
                            assign[account][policy][device]['requests'] += 1
                    	if not 'ips' in assign[account][policy][device]:
                            assign[account][policy][device]['ips'] = set()
                        assign[account][policy][device]['ips'].add(ip)
	    
            for policy in assign[account]:
		for device in assign[account][policy]:
                    for ip in assign[account][policy][device]['ips']:
                        try:
                            bw_a[account][ip+"-"+policy+"-"+device] = int(bw[account][policy])/assign[account][policy][device]['requests']
                        except Exception as e:
			    print "ERROR: "+str(e)
                            #ibw_a[account][ip+"-"+policy+"-"+device] = -1

        return bw_a
	'''

    def get_redis_bw(self):
        """
        Gets the bw assignation from the redis database
        """
        bw = dict()
        keys = self.r.keys("bw:*")
        for key in keys:
            bw[key[3:]] = self.r.hgetall(key)
        return bw

    def send_results(self, assign):
        routing_key = "."
        address = " "
        send = False

        for account in assign:
            for ip in assign[account]:		
                new_flow = account not in self.last_bw or ip not in self.last_bw[account]
                if not new_flow and int(assign[account][ip]) == int(self.last_bw[account][ip]):
                    break
                ip_c = ip.split('-')
                address = ip_c[0]+'/'+account+'/'+ ip_c[1]+'/'+ip_c[2]+'/'+str(assign[account][ip])
		routing_key = '.'+ip_c[0].replace('.','-').replace(':','-') + "."
		#print routing_key
                print "BW CHANGED: "+ str(address) 
                self.send_message_rmq(address, routing_key)

    def get_tenant(self):
        """
        Return the tenant assigned to this rule.

        :return: Return the tenant id assigned to this rule
        :rtype: String type.
        """
        return self.tenant
