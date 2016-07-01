from rule import Rule
import requests
import json


class TransientRule(Rule):
    """
    TransientRule: Each policy of each tenant is compiled as Rule. Rule is an Actor and it will be subscribed
    in the workloads metrics. When the data received from the workloads metrics satisfies
    the conditions defined in the policy,the Rule actor executes an Action that it is
    also defined in the policy. Once executed the action, if change the condition evaluation
    the rule will execute the reverse action (if action is SET, the will execute DELETE)
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
        """
        print "-- Rule Transient --"
        self.execution_stat = False
        super(TransientRule, self).__init__(rule_parsed, action, target, remote_host)

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

        self.observers_values[metric] = tenant_info.value
        
        if all(val is not None for val in self.observers_values.values()):
            condition_accomplished = self.check_conditions(self.conditions)
            if condition_accomplished != self.execution_stat:
                self.do_action(condition_accomplished)
                self.execution_stat = condition_accomplished
            
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

        headers = {"X-Auth-Token": self.token}
        dynamic_filter = self.redis.hgetall("filter:"+str(self.action_list.filter))

        if action == "SET":

            # TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.

            url = dynamic_filter["activation_url"]+"/"+self.target+"/deploy/"+str(dynamic_filter["identifier"])
            print 'params: ', self.action_list.params
            
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code

        elif action == "DELETE":
            print "Deleteing filter"
            url = dynamic_filter["activation_url"]+"/"+self.target+"/undeploy/"+str(dynamic_filter["identifier"])
            response = requests.put(url, json.dumps(self.action_list.params), headers=headers)

            if 200 > response.status_code >= 300:
                print 'ERROR RESPONSE'
            else:
                print response.text, response.status_code

        return 'Not action supported'
