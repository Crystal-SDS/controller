import requests
import operator
import json
import redis
import logging
import ConfigParser

mappings = {'>': operator.gt, '>=': operator.ge,
            '==': operator.eq, '<=': operator.le, '<': operator.lt,
            '!=': operator.ne, "OR": operator.or_, "AND": operator.and_}

logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class Rule(object):
    """
    Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
    in the workloads metrics. When the data received from the workloads metrics satisfies
    the conditions defined in the policy,the Rule actor executes an Action that it is
    also defined in the policy. Once the rule executed the action, this actor is destroyed.
    """
    _sync = {'get_target': '2'}
    _async = ['update', 'start_rule', 'stop_actor']
    _ref = []
    _parallel = []

    def __init__(self, rule_parsed, action, target, remote_host):
        """
        Initialize all the variables needed for the rule.

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param target: The target assigned to this rule.
        :type target: **any** String type
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
        logging.info('Rule: %s', rule_parsed.asList())

        settings = ConfigParser.ConfigParser()
        settings.read("./dynamic_policies.config")
        
        self.openstack_tenant = settings.get('openstack', 'admin_tenant')
        self.openstack_user = settings.get('openstack', 'admin_name')
        self.openstack_pass = settings.get('openstack', 'admin_pass')
        self.openstack_keystone_url = settings.get('openstack', 'keystone_url')

        self.redis_host = settings.get('redis', 'host')
        self.redis_port = int(settings.get('redis', 'port'))
        self.redis_db = int(settings.get('redis', 'db'))
        
        self.redis = redis.StrictRedis(host=self.redis_host, port=self.redis_port, db=self.redis_db)
        
        self.remote_host = remote_host
        self.rule_parsed = rule_parsed
        self.target = target
        self.conditions = rule_parsed.condition_list.asList()
        self.observers_values = {}
        self.observers_proxies = {}
        self.action_list = action
        self.token = None

    def admin_login(self):
        """
        Method called to obtain the admin credentials, which we need to deploy filters in accounts.
        """
        body = json.dumps({"auth": {"tenantName": self.openstack_tenant, "passwordCredentials": {"username": self.openstack_user,
                                                                                                 "password": self.openstack_pass}}})
        headers = {"Content-type": "application/json"}
        
        r = requests.post(self.openstack_keystone_url, data=body, headers=headers)
        if r.status_code == 200:
            self.token = r.json()["access"]["token"]["id"]
        else:
            raise Exception("Problems with the admin user credentials located in the config file")

    def stop_actor(self):
        """
        Method called to end the rule. This method unsubscribes the rule from all the workload metrics subscribed, and
        kills the actor of the rule.
        """
        for observer in self.observers_proxies.values():
            observer.detach(self.proxy)
        self.redis.hset(str(self.id), "alive", False)
        self._atom.stop()
        print 'Actor rule stopped'

    def start_rule(self):
        """
        Method called afeter init to start the rule. Basically this method allows to be called remotelly and calls the
        internal method **check_metrics()** which subscribes the rule to all the workload metrics necessaries.
        """
        print 'Start rule'
        self.check_metrics(self.conditions)

    def add_metric(self, workload_name):
        """
        The `add_metric()` method subscribes the rule to all workload metrics that it
        needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        print 'hello into add metric'
        print "--> WN:", workload_name
        if workload_name not in self.observers_values.keys():
            # Trying the new PyActive version. New lookup function.
            print 'workload_name', workload_name
            observer = self.remote_host.lookup(workload_name)
            print 'observer', observer, observer.get_id()
            observer.attach(self.proxy)
            self.observers_proxies[workload_name] = observer
            self.observers_values[workload_name] = None

    def check_metrics(self, condition_list):
        """
        The check_metrics method finds in the condition list all the metrics that it
        needs to check the conditions, when find some metric that it needs, call the
        method add_metric.

        :param condition_list: The list of all the conditions.
        :type condition_list: **any** List type
        """
        print 'check_metrics', condition_list
        if not isinstance(condition_list[0], list):
            self.add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)

    def update(self, metric, value):
        """
        The method update is called by the workloads metrics following the observer
        pattern. This method is called to send to this actor the data updated.

        :param metric: The name that identifies the workload metric.
        :type metric: **any** String type

        :param tenant_info: Contains the timestamp and the value sent from workload metric.
        :type tenant_info: **any** PyParsing type
        """
        print 'Success update:  ', value

        self.observers_values[metric] = value
        
        print self.observers_values

        # TODO Check the last time updated the value
        # Check the condition of the policy if all values are setted. If the condition
        # result is true, it calls the method do_action
        if all(val is not None for val in self.observers_values.values()):
            if self.check_conditions(self.conditions):
                self.do_action()
        else:
            print 'not all values setted', self.observers_values.values()

    def check_conditions(self, condition_list):
        """
        The method **check_conditions()** runs the ternary tree of conditions to check if the
        **self.observers_values** complies the conditions. If the values comply the conditions return
        True, else return False.

        :param condition_list: A list of all the conditions
        :type condition_list: **any** List type

        :return: If the values comply the conditions
        :rtype: boolean type.
        """
        if not isinstance(condition_list[0], list):
            result = mappings[condition_list[1]](float(self.observers_values[condition_list[0].lower()]), float(condition_list[2]))
        else:
            result = self.check_conditions(condition_list[0])
            for i in range(1, len(condition_list)-1, 2):
                result = mappings[condition_list[i]](result, self.check_conditions(condition_list[i+1]))
        return result

    def get_target(self):
        """
        Retrun the target assigned to this rule.

        :return: Return the target id assigned to this rule
        :rtype: String type.
        """
        return self.target

    def do_action(self):
        """
        The do_action method is called after the conditions are satisfied. So this method
        is responsible to execute the action defined in the policy.

        """

        if not self.token:
            self.admin_login()

        headers = {"X-Auth-Token": self.token}

        dynamic_filter = self.redis.hgetall("dsl_filter:"+str(self.action_list.filter))      
        
        if self.action_list.action == "SET":
            # TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.

            url = dynamic_filter["activation_url"]+"/"+self.target+"/deploy/"+str(dynamic_filter["identifier"])

            data = dict()
            
            if hasattr(self.rule_parsed.object_list, "object_type"):
                data['object_type'] = self.rule_parsed.object_list.object_type.object_value
            else:
                data['object_type'] = ''
 
            if hasattr(self.rule_parsed.object_list, "object_size"):
                data['object_size'] = self.rule_parsed.object_list.object_size.object_value
            else:
                data['object_size'] = ''

            data['params'] = self.action_list.params
            
            response = requests.put(url, json.dumps(data), headers=headers)

            if 200 > response.status_code >= 300:
                print 'Error setting policy'
            else:
                print "Policy applied"
                self.stop_actor()  # TODO: stop_actor shows timeout error

        elif self.action_list.action == "DELETE":
            print "--> DELETE <--"

            url = dynamic_filter["activation_url"]+"/"+self.target+"/undeploy/"+str(dynamic_filter["identifier"])
            response = requests.put(url, headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code
                self.stop_actor()
                return response.text

        return 'Not action supported'
