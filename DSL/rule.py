from rules_parse import parse
import operator
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
from requests_oauthlib import OAuth1, OAuth1Session
import json

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}
base_url = "http://localhost:18000/"

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

        self.base_uri = host_transport+'://'+host_ip+':'+str(host_port)+'/metric/'
        tcpconf = (host_transport,(host_ip, host_port))
        self.host = host
        self.action_list = rule_parsed.action_list

    def start_rule(self):
        f = open('actions_success_'+str(self.id)+'.txt', 'a')
        f.write("RULE = "+str(self.rule_parsed.asList()))
        f.close()
        self.check_metrics(self.conditions)

    def add_metric(self, value):
        if value not in self.observers.keys():
            #Subscrive to metric observer
            observer = self.host.lookup(self.base_uri+value.title()+'/'+value)
            observer.attach(self.proxy)
            self.observers[value] = None

    def check_metrics(self, condition_list):
        if not isinstance(condition_list[0], list):
            self.add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)

    def update(self, metric, tenant_info):

        self.observers[metric]=tenant_info[metric]
        #TODO Check the last time updated the value
        if all(val!=None for val in self.observers.values()):
            result = self.check_conditions(self.conditions)
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

    def do_action(self):
        # TODO: Call SDS Controller API functions
        f = open('actions_success_'+str(self.id)+'.txt', 'a')
        f.write(str(self.id)+": "+str(self.observers.values())+"\n")

        headers = {"X-Auth-Token":"3fc0ccfec1954f25bef393d2c39499e7"}
        if self.action_list.action == "SET":
            url = base_url+"filters/"+self.tenant+"/deploy/"+self.action_list.filter
            print 'url: ', url
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)
            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code
                f.write(str(self.id)+": "+str(response.text)+"\n")
                f.close()

        if self.action_list.action == "DELETE":
            url = base_url+"filters/"+self.tenant+"/undeploy/"+self.action_list.filter
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)
            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code
        return 'hola que tal!! :D'
