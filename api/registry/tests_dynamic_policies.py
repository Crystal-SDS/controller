import os
import mock
import redis

from django.conf import settings
from django.test import TestCase, override_settings

from .dsl_parser import parse
from registry.dynamic_policies.rules.rule import Rule


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "native_metrics"))
class DynamicPoliciesTestCase(TestCase):

    def setUp(self):
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

    def tearDown(self):
        self.r.flushdb()

    def test_get_target_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = Rule(parsed_rule, parsed_rule.action_list[0], target, host)
        self.assertEqual(rule.get_target(), '4f0279da74ef4584a29dc72c835fe2c9')

    @mock.patch('registry.dynamic_policies.rules.rule.Rule._do_action')
    def test_action_is_not_triggered(self, mock_do_action):
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = Rule(parsed_rule, parsed_rule.action_list[0], target, host)
        rule.update('metric1', 3)
        self.assertFalse(mock_do_action.called)

    @mock.patch('registry.dynamic_policies.rules.rule.Rule._do_action')
    def test_action_is_triggered(self, mock_do_action):
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = Rule(parsed_rule, parsed_rule.action_list[0], target, host)
        rule.update('metric1', 6)
        self.assertTrue(mock_do_action.called)

    #
    # Aux methods
    #

    def setup_dsl_parser_data(self):
        self.r.hmset('dsl_filter:compression', {'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'})
        self.r.hmset('dsl_filter:encryption', {'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})