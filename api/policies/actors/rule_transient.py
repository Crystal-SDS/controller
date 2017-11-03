from rule import Rule
import requests
import logging
import json
import os

logger = logging.getLogger(__name__)


class TransientRule(Rule):
    """
    TransientRule: Each policy of each tenant is compiled as Rule. Rule is an
    Actor and it will be subscribed in the workloads metrics. When the data
    received from the workloads metrics satisfies the conditions defined in the
    policy,the Rule actor executes an Action that it is also defined in the
    policy. Once executed the action, if change the condition evaluation  the
    rule will execute the reverse action (if action is SET, the will execute
    DELETE)
    """
    _ask = ['get_target']
    _async = ['update', 'start_rule', 'stop_actor']

    def __init__(self, policy_data, controller_server):
        """
        Initialize all the variables needed for the rule.

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param target_name: The target assigned to this rule.
        :type target_name: **any** String type
        """
        super(TransientRule, self).__init__(policy_data, controller_server)
        logger.info("Transient Rule")
        self.execution_stat = False
        self.static_policy_id = None

    def update(self, metric, tenant_info):
        """
        The method update is called by the workloads metrics following the
        observer pattern. This method is called to send to this actor the
        data updated.

        :param metric: The name that identifies the workload metric.
        :type metric: **any** String type

        :param tenant_info: Contains the timestamp and the value sent from
                            workload metric.
        :type tenant_info: **any** PyParsing type
        """
        logger.info('Success update: ' + str(tenant_info))

        self.observers_values[metric] = tenant_info

        if all(val is not None for val in self.observers_values.values()):
            condition_accomplished = self._check_conditions(self.condition_list)
            if condition_accomplished != self.execution_stat:
                self.do_action(condition_accomplished)
                self.execution_stat = condition_accomplished

    def do_action(self, condition_result):
        """
        The do_action method is called after the conditions are satisfied. So
        this method is responsible to execute the action defined in the policy.
        """
        if not condition_result and self.action == "SET":
            action = "DELETE"
        elif not condition_result and self.action == "DELETE":
            action = "SET"
        else:
            action = self.action

        if not self.token:
            self._get_admin_token()

        headers = {"X-Auth-Token": self.token}

        if action == "SET":
            # TODO Review if this tenant has already deployed this filter. Don't deploy the same filter more than one time.
            logger.info("Setting static policy")
            data = dict()
            url = os.path.join('http://'+self.controller_server, 'filters', self.target_id, "deploy", str(self.filter))

            data['object_type'] = self.object_type
            data['object_size'] = self.object_size
            data['object_tag'] = self.object_tag

            data['params'] = self.params

            response = requests.put(url, json.dumps(data), headers=headers)

            if 200 <= response.status_code < 300:
                logger.info("Static policy applied with ID: " + response.content)
                self.static_policy_id = response.content
            else:
                logger.error('Error setting policy')

        elif action == "DELETE":
            logger.info("Deleting static policy " + str(self.static_policy_id))
            url = os.path.join('http://'+self.controller_server, "policies/static", self.target_id+":"+str(self.static_policy_id))
            response = requests.delete(url, headers=headers)

            if 200 <= response.status_code < 300:
                logger.info("Policy " + str(self.static_policy_id) + " successfully deleted")
            else:
                logger.error('Error Deleting policy')

        return 'Not action supported'
