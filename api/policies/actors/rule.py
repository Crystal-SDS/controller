from swiftclient import client as c
import json
import operator
import logging
import redis
import requests
import os
from policies.dsl_parser import parse_condition

from api.settings import MANAGEMENT_ACCOUNT, MANAGEMENT_ADMIN_USERNAME, \
    MANAGEMENT_ADMIN_PASSWORD, KEYSTONE_ADMIN_URL, REDIS_HOST, REDIS_PORT, REDIS_DATABASE

mappings = {'>': operator.gt, '>=': operator.ge,
            '==': operator.eq, '<=': operator.le, '<': operator.lt,
            '!=': operator.ne, "OR": operator.or_, "AND": operator.and_}
logger = logging.getLogger(__name__)


class Rule(object):
    """
    Rule: Each policy of each tenant is compiled as Rule. Rule is an Actor and
    it will be subscribed in the workloads metrics. When the data received from
    the workloads metrics satisfies the conditions defined in the policy,the
    Rule actor executes an Action that it is also defined in the policy. Once
    the rule executed the action, this actor is destroyed.
    """
    _ask = ['get_target', 'start_rule']
    _tell = ['update', 'stop_actor']

    def __init__(self, policy_data, controller_server):
        """
        Initialize all the variables needed for the rule.

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param action: The action assigned to this rule.
        :type action: **any** PyParsing type
        :param target: The target assigned to this rule.
        :type target: **any** String type
        :param host: The proxy host provided by the PyActor Middleware.
        :type host: **any** PyActor Proxy type
        """

        self.admin_project = MANAGEMENT_ACCOUNT
        self.admin_user = MANAGEMENT_ADMIN_USERNAME
        self.admin_pass = MANAGEMENT_ADMIN_PASSWORD
        self.admin_keystone_url = KEYSTONE_ADMIN_URL

        self.redis_host = REDIS_HOST
        self.redis_port = REDIS_PORT
        self.redis_db = REDIS_DATABASE

        self.redis = redis.StrictRedis(host=self.redis_host,
                                       port=self.redis_port,
                                       db=self.redis_db)

        self.action = policy_data['action']
        self.filter = policy_data['filter']
        self.params = policy_data['parameters']
        self.target_id = policy_data['target_id']
        self.target_name = policy_data['target_name']
        self.object_size = policy_data['object_size']
        self.object_tag = policy_data['object_tag']
        self.object_type = policy_data['object_type']
        self.controller_server = controller_server
        self.condition = policy_data['condition']
        self.observers_values = dict()
        self.observers_proxies = dict()
        self.token = None
        self.applied = False

    def _get_admin_token(self):
        """
        Method called to obtain the admin credentials, which we need to deploy
        filters in accounts.
        """
        try:
            _, self.token = c.get_auth(self.admin_keystone_url,
                                       self.admin_project+":"+self.admin_user,
                                       self.admin_pass, auth_version="3")
        except:
            logger.error("Rule, There was an error gettting a token from keystone")
            raise Exception()

    def stop_actor(self):
        """
        Method called to end the rule. This method unsubscribes the rule from
        all the workload metrics subscribed, and kills the actor of the rule.
        """
        for observer in self.observers_proxies.values():
            observer.detach(self.id, self.get_target())
        self.host.stop_actor(self.id)
        logger.info("Rule, Actor '" + str(self.id) + "' stopped")

    def start_rule(self):
        """
        Method called after init to start the rule. Basically this method
        allows to be called remotely and calls the internal method
        **check_metrics()** which subscribes the rule to all the workload
        metrics necessaries.
        """
        try:
            self.condition_list = parse_condition(self.condition)
        except:
            raise ValueError("Workload Metric not started")
        logger.info("Rule, Start '" + str(self.id) + "'")
        logger.info('Rule, Conditions: ' + str(self.condition))

        self.check_metrics(self.condition_list)

    def check_metrics(self, condition_list):
        """
        The check_metrics method finds in the condition list all the metrics
        that it needs to check the conditions, when find some metric that it
        needs, call the method add_metric.
        :param condition_list: The list of all the conditions.
        :type condition_list: **any** List type
        """
        if not isinstance(condition_list[0], list):
            self._add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)

    def _add_metric(self, metric_name):
        """
        This method subscribes the rule to the metric_name
        that it needs to check the conditions defined in the policy

        :param metric_name: The name that identifies the workload metric.
        :type metric_name: **any** String type

        """
        if metric_name not in self.observers_values.keys():
            logger.info("Rule, Workload metric: " + metric_name)
            observer = self.host.lookup(metric_name)
            logger.info('Rule, Observer: ' + str(observer.get_id()) + " " + str(observer))
            observer.attach(self.proxy)
            self.observers_proxies[metric_name] = observer
            self.observers_values[metric_name] = None

    def update(self, metric_name, value):
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
        logger.info("Rule, Success update: " + str(metric_name) + " = " + str(value))

        self.observers_values[metric_name] = value

        # TODO Check the last time updated the value
        # Check the condition of the policy if all values are setted. If the
        # condition result is true, it calls the method do_action
        if all(val is not None for val in self.observers_values.values()):
            if self._check_conditions(self.condition_list):
                self._do_action()
        else:
            logger.error("not all values setted" + str(self.observers_values.values()))

    def _check_conditions(self, condition_list):
        """
        The method **check_conditions()** runs the ternary tree of conditions
        to check if the **self.observers_values** complies the conditions. If
        the values comply the conditions return True, else return False.

        :param condition_list: A list of all the conditions
        :type condition_list: **any** List type

        :return: If the values comply the conditions
        :rtype: boolean type.
        """
        if not isinstance(condition_list[0], list):
            result = mappings[condition_list[1]](float(self.observers_values[condition_list[0].lower()]), float(condition_list[2]))
        else:
            result = self.check_conditions(condition_list[0])
            for i in range(1, len(condition_list) - 1, 2):
                result = mappings[condition_list[i]](result, self.check_conditions(condition_list[i + 1]))
        return result

    def get_target(self):
        """
        Return the target assigned to this rule.

        :return: Return the target name assigned to this rule
        :rtype: String type.
        """
        # return self.target_id
        return self.target_name

    def _do_action(self):
        """
        The do_action method is called after the conditions are satisfied. So
        this method is responsible to execute the action defined in the policy.
        """
        if self.applied:
            return
        else:
            self.applied = True
        if not self.token:
            self._get_admin_token()

        headers = {"X-Auth-Token": self.token}

        if self.action == "SET":
            # TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.

            url = os.path.join('http://'+self.controller_server, 'filters', self.target_id, "deploy", str(self.filter))

            data = dict()

            data['object_type'] = self.object_type
            data['object_size'] = self.object_size
            data['object_tag'] = self.object_tag
            data['params'] = self.params

            response = requests.put(url, json.dumps(data), headers=headers)

            if 200 <= response.status_code < 300:
                logger.info('Policy ' + str(self.id) + ' applied')
                self.redis.hset(self.id, 'status', 'Applied')
                try:
                    self.stop_actor()
                except:
                    pass
                return
            else:
                logger.error('Error setting policy')

        elif self.action == "DELETE":

            url = os.path.join('http://'+self.controller_server, 'filters', self.target_id, "undeploy", str(self.filter))
            response = requests.put(url, headers=headers)

            if 200 <= response.status_code < 300:
                logger.info(response.text + " " + str(response.status_code))
                try:
                    self.stop_actor()
                except:
                    pass
                return response.text
            else:
                logger.error('ERROR RESPONSE')

        return 'Not action supported'
