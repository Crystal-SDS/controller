
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import operator
import json
import redis
import logging
from rule import Rule
mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

#TODO: Add the redis connection into rule object
r = redis.StrictRedis(host='localhost', port=6379, db=0)
logging.basicConfig(filename='./rule.log', format='%(asctime)s %(message)s', level=logging.INFO)


class TransientRule(Rule):
    """
    Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
    in the workloads metrics. When the data received from the workloads metrics satisfies
    the conditions defined in the policy,the Rule actor executes an Action that it is
    also defined in the policy.
    """
    _sync = {'get_tenant':'2'}
    _async = ['update', 'start_rule', 'stop_actor']
    _ref = []
    _parallel = []

    def __init__(self, rule_parsed, target, host, host_ip, host_port, host_transport):
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
        self.execution_stat = False
        super(TrancientRule, self).__init__(rule_parsed, target, host, host_ip, host_port, host_transport)


    def update(self, metric, tenant_info):
        """
        The method update is called by the workloads metrics following the observer
        pattern. This method is called to send to this actor the data updated.

        :param metric: The name that identifies the workload metric.
        :type metric: **any** String type

        :param tenant_info: Contains the timestamp and the value sent from workload metric.
        :type tenant_info: **any** PyParsing type
        """
        print 'Success update:  ', tenant_info

        self.observers_values[metric]=tenant_info.value
        #TODO Check the last time updated the value
        #Check the condition of the policy if all values are setted. If the condition
        #result is true, it calls the method do_action
        if all(val!=None for val in self.observers_values.values()):
            if self.check_conditions(self.conditions) and not self.execution_stat:
                self.do_action(True)
                self.execution_stat = True
        elif self.execution_stat:
            self.do_action(False)
            self.execution_stat = False
            print 'not all values setted', self.observers_values.values()

    def do_action(self, condition_result):
        """
        The do_action method is called after the conditions are satisfied. So this method
        is responsible to execute the action defined in the policy.

        """
        if not condition_result and self.action_list.action == "SET":
            action = "DELETE"
        elif not condition_result and self.action_list.action == "DELETE":
            action = "SET"
        else:
            action = self.action_list.action

        if not self.token:
            self.admin_login()

        headers = {"X-Auth-Token":self.token}
        dynamic_filter = r.hgetall("filter:"+str(self.action_list.filter))

        if action == "SET":

            #TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.

            url = dynamic_filter["activation_url"]+"/"+self.target+"/deploy/"+str(dynamic_filter["identifier"])
            print 'params: ', self.action_list.params
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code


        elif action == "DELETE":

            url = dynamic_filter["activation_url"]+"/"+self.target+"/undeploy/"+str(dynamic_filter["identifier"])
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code


        return 'Not action supported'
