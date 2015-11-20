
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import operator
import json

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}
base_url = "http://localhost:18000/"


"""
Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
in the workloads metrics. When the data received from the workloads metrics satisfies
the conditions defined in the policy,the Rule actor executes an Action that it is
also defined in the policy.
"""
class Rule(object):

    _sync = {'get_tenant':'2'}
    _async = ['update', 'start_rule']
    _ref = []
    _parallel = []

    def __init__(self, rule_parsed, tenant, host, host_ip, host_port, host_transport):
        self.rule_parsed = rule_parsed
        self.tenant = tenant
        self.conditions = rule_parsed.condition_list.asList()
        self.observers = {}

        self.base_uri = host_transport+'://'+host_ip+':'+str(host_port)+'/'
        tcpconf = (host_transport,(host_ip, host_port))
        self.host = host
        self.action_list = rule_parsed.action_list

    def start_rule(self):
        f = open('actions_success_'+str(self.id)+'.txt', 'a')
        f.write("RULE = "+str(self.rule_parsed.asList()))
        f.close()
        self.check_metrics(self.conditions)

    """
    The add_metric method subscribes the rule to all workload metrics that it
    needs to check the conditions defined in the policy
    """
    def add_metric(self, value):
        if value not in self.observers.keys():
            #Subscrive to metric observer
            observer = self.host.lookup(self.base_uri+'metrics.'+value+'/'+value.title()+'/'+value)
            observer.attach(self.proxy)
            self.observers[value] = None
    """
    The check_metrics method finds in the condition list all the metrics that it
    needs to check the conditions, when find some metric that it needs, call the
    method add_metric.
    """
    def check_metrics(self, condition_list):
        if not isinstance(condition_list[0], list):
            self.add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)
    """
    The method update is called by the workloads metrics following the observer
    pattern. This method is called to send to this actor the data updated.
    """
    def update(self, metric, tenant_info):

        self.observers[metric]=tenant_info[metric]
        #TODO Check the last time updated the value
        #Check the condition of the policy if all values are setted. If the condition
        #result is true, it calls the method do_action
        if all(val!=None for val in self.observers.values()):
            if self.check_conditions(self.conditions):
                print self.do_action()
        else:
            print 'not all values setted', self.observers.values()

    def check_conditions(self, condition_list):
        if not isinstance(condition_list[0], list):
            result = mappings[condition_list[1]](float(self.observers[condition_list[0].lower()]), float(condition_list[2]))
        else:
            result = self.check_conditions(condition_list[0])
            for i in range(1, len(condition_list)-1, 2):
                result = mappings[condition_list[i]](result, self.check_conditions(condition_list[i+1]))
        return result

    def get_tenant(self):
        return self.tenant

    """
    The do_action method is called after the conditions are satisfied. So this method
    is responsible to execute the action defined in the policy.
    """
    def do_action(self):
        # TODO: Add registry to save the action. Here it needs to ask for the action in the registry

        #create file to test
        f = open('actions_success_'+str(self.id)+'.txt', 'a')
        f.write(str(self.id)+": "+str(self.observers.values())+"\n")

        headers = {"X-Auth-Token":"3fc0ccfec1954f25bef393d2c39499e7"}

        if self.action_list.action == "SET":
            url = base_url+"filters/"+self.tenant+"/deploy/"+self.action_list.filter
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code
                f.write(str(self.id)+": "+str(response.text)+"\n")
                f.close()
                return response.text

        elif self.action_list.action == "DELETE":
            url = base_url+"filters/"+self.tenant+"/undeploy/"+self.action_list.filter
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code
                return response.text

        return 'Not action supported'
