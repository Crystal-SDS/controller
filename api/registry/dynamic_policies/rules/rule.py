import json
import operator
import logging
import redis
import requests

from api.settings import MANAGEMENT_ACCOUNT, MANAGEMENT_ADMIN_USERNAME, MANAGEMENT_ADMIN_PASSWORD, KEYSTONE_ADMIN_URL, REDIS_HOST, REDIS_PORT, REDIS_DATABASE

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
    _sync = {'get_target': '2'}
    _async = ['update', 'start_rule', 'stop_actor']
    _ref = []
    _parallel = []

    def __init__(self, rule_parsed, action, target, host):
        """
        Initialize all the variables needed for the rule.

        :param rule_parsed: The rule parsed by the dsl_parser.
        :type rule_parsed: **any** PyParsing type
        :param action: The action assigned to this rule.
        :type action: **any** PyParsing type
        :param target: The target assigned to this rule.
        :type target: **any** String type
        :param host: The proxy host provided by the PyActive Middleware.
        :type host: **any** PyActive Proxy type
        """

        # settings = ConfigParser.ConfigParser()
        # settings.read("registry/dynamic_policies/settings.conf")

        self.openstack_tenant = MANAGEMENT_ACCOUNT
        self.openstack_user = MANAGEMENT_ADMIN_USERNAME
        self.openstack_pass = MANAGEMENT_ADMIN_PASSWORD
        self.openstack_keystone_url = KEYSTONE_ADMIN_URL

        self.redis_host = REDIS_HOST
        self.redis_port = REDIS_PORT
        self.redis_db = REDIS_DATABASE

        self.redis = redis.StrictRedis(host=self.redis_host,
                                       port=self.redis_port,
                                       db=self.redis_db)

        self.host = host
        self.rule_parsed = rule_parsed
        self.target = target
        self.conditions = rule_parsed.condition_list.asList()
        self.observers_values = dict()
        self.observers_proxies = dict()
        self.action_list = action
        self.token = None

    def _admin_login(self):
        """
        Method called to obtain the admin credentials, which we need to deploy
        filters in accounts.
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
        Method called to end the rule. This method unsubscribes the rule from
        all the workload metrics subscribed, and kills the actor of the rule.
        """
        for observer in self.observers_proxies.values():
            observer.detach(self.proxy, self.get_target())
        self._atom.stop()
        logger.info("Rule, Actor '" + self.id + "' stopped")

    def start_rule(self):
        """
        Method called afeter init to start the rule. Basically this method
        allows to be called remotely and calls the internal method
        **check_metrics()** which subscribes the rule to all the workload
        metrics necessaries.
        """
        logger.info("Rule, Start '" + self.id + "'")
        self.check_metrics(self.conditions)

    def _add_metric(self, workload_name):
        """
        The `add_metric()` method subscribes the rule to all workload metrics
        that it needs to check the conditions defined in the policy

        :param workload_name: The name that identifies the workload metric.
        :type workload_name: **any** String type

        """
        if workload_name not in self.observers_values.keys():
            # Trying the new PyActive version. New lookup function.
            logger.info("Rule, Workload name:", workload_name)
            observer = self.host.lookup(workload_name)
            logger.info('Rule, Observer: ' + observer.get_id() + " " + observer)
            observer.attach(self.proxy)
            self.observers_proxies[workload_name] = observer
            self.observers_values[workload_name] = None

    def check_metrics(self, condition_list):
        """
        The check_metrics method finds in the condition list all the metrics
        that it needs to check the conditions, when find some metric that it
        needs, call the method add_metric.

        :param condition_list: The list of all the conditions.
        :type condition_list: **any** List type
        """
        logger.info('Rule, Condition: ' + str(condition_list))
        if not isinstance(condition_list[0], list):
            self._add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)

    def update(self, metric, value):
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
        logger.info("--> Success update: " + value)

        self.observers_values[metric] = value

        # TODO Check the last time updated the value
        # Check the condition of the policy if all values are setted. If the
        # condition result is true, it calls the method do_action
        if all(val is not None for val in self.observers_values.values()):
            if self._check_conditions(self.conditions):
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

        :return: Return the target id assigned to this rule
        :rtype: String type.
        """
        return self.target

    def _do_action(self):
        """
        The do_action method is called after the conditions are satisfied. So
        this method is responsible to execute the action defined in the policy.
        """
        if not self.token:
            self._admin_login()

        headers = {"X-Auth-Token": self.token}
        dynamic_filter = self.redis.hgetall("dsl_filter:" + str(self.action_list.filter))

        if self.action_list.action == "SET":
            # TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.

            url = dynamic_filter["activation_url"] + "/" + self.target + "/deploy/" + str(dynamic_filter["identifier"])

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

            if 200 <= response.status_code < 300:
                logger.info('Policy ' + self.id + ' applied')
                self.redis.hset(self.id, 'alive', False)
                try:
                    self.stop_actor()
                except:
                    pass
                return
            else:
                logger.error('Error setting policy')

        elif self.action_list.action == "DELETE":
            logger.info("--> DELETE <--")

            url = dynamic_filter["activation_url"] + "/" + self.target + "/undeploy/" + str(dynamic_filter["identifier"])
            response = requests.put(url, headers=headers)

            if 200 <= response.status_code < 300:
                logger.info(response.text + " " + response.status_code)
                try:
                    self.stop_actor()
                except:
                    pass
                return response.text
            else:
                logger.error('ERROR RESPONSE')

        return 'Not action supported'
