import json
import os
import mock
import redis

from django.conf import settings
from django.test import TestCase, override_settings

from .dsl_parser import parse
from registry.dynamic_policies.rules.rule import Rule
from registry.dynamic_policies.rules.rule_transient import TransientRule
from registry.dynamic_policies.metrics.bw_info import BwInfo
from registry.dynamic_policies.metrics.swift_metric import SwiftMetric

from httmock import urlmatch, HTTMock

@urlmatch(netloc=r'(.*\.)?example\.com')
def example_mock_200(url, request):
    return {'status_code': 200, 'content': 'OK'}

@urlmatch(netloc=r'(.*\.)?example\.com')
def example_mock_400(url, request):
    return {'status_code': 400, 'content': 'Error'}


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "native_metrics"))
class DynamicPoliciesTestCase(TestCase):

    def setUp(self):
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

    def tearDown(self):
        self.r.flushdb()

    #
    # rules/rule
    #


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

    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hgetall')
    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hset')
    @mock.patch('registry.dynamic_policies.rules.rule.Rule._admin_login')
    def test_action_set_is_triggered_deploy_200(self, mock_admin_login, mock_redis_hset, mock_redis_hgetall):
        mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
                                           'identifier': '1',
                                           'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = Rule(parsed_rule, parsed_rule.action_list[0], target, host)
        rule.id = '10'
        with HTTMock(example_mock_200):
            rule.update('metric1', 6)
        self.assertTrue(mock_admin_login.called)
        self.assertTrue(mock_redis_hset.called)
        mock_redis_hset.assert_called_with('10', 'alive', False)

    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hgetall')
    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hset')
    @mock.patch('registry.dynamic_policies.rules.rule.Rule._admin_login')
    def test_action_set_is_triggered_deploy_400(self, mock_admin_login, mock_redis_hset, mock_redis_hgetall):
        mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
                                           'identifier': '1',
                                           'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = Rule(parsed_rule, parsed_rule.action_list[0], target, host)
        rule.id = '10'
        with HTTMock(example_mock_400):
            rule.update('metric1', 6)
        self.assertTrue(mock_admin_login.called)
        self.assertFalse(mock_redis_hset.called)

    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hgetall')
    @mock.patch('registry.dynamic_policies.rules.rule.Rule._admin_login')
    @mock.patch('registry.dynamic_policies.rules.rule.Rule.stop_actor')
    def test_action_delete_is_triggered_undeploy_200(self, mock_stop_actor, mock_admin_login, mock_redis_hgetall):
        mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
                                           'identifier': '1',
                                           'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        action = parsed_rule.action_list[0]
        action.action = 'DELETE'
        rule = Rule(parsed_rule, action, target, host)
        rule.id = '10'
        with HTTMock(example_mock_200):
            rule.update('metric1', 6)
        self.assertTrue(mock_admin_login.called)
        self.assertTrue(mock_stop_actor.called)

    #
    # rules/rule_transient
    #

    @mock.patch('registry.dynamic_policies.rules.rule_transient.TransientRule.do_action')
    def test_transient_action_is_triggered(self, mock_do_action):
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression TRANSIENT')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = TransientRule(parsed_rule, parsed_rule.action_list[0], target, host)
        rule.update('metric1', 6)
        self.assertTrue(mock_do_action.called)

    @mock.patch('registry.dynamic_policies.rules.rule.redis.StrictRedis.hgetall')
    @mock.patch('registry.dynamic_policies.rules.rule_transient.TransientRule._admin_login')
    @mock.patch('registry.dynamic_policies.rules.rule_transient.requests.put')
    @mock.patch('registry.dynamic_policies.rules.rule_transient.requests.delete')
    def test_transient_action_set_is_triggered_200(self, mock_requests_delete, mock_requests_put, mock_admin_login, mock_redis_hgetall):
        mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
                                           'identifier': '1',
                                           'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
        self.setup_dsl_parser_data()
        has_condition_list, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression TRANSIENT')
        target = '4f0279da74ef4584a29dc72c835fe2c9'
        host = None
        rule = TransientRule(parsed_rule, parsed_rule.action_list[0], target, host)

        rule.update('metric1', 6)
        self.assertTrue(mock_requests_put.called)
        self.assertFalse(mock_requests_delete.called)
        mock_requests_put.reset_mock()
        mock_requests_delete.reset_mock()
        rule.static_policy_id = 'FAKE_ID'
        rule.update('metric1', 4)
        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)

    #
    # metrics/bw_info
    #

    @mock.patch('registry.dynamic_policies.metrics.swift_metric.Thread.start')
    def test_metrics_bw_info(self, mock_thread_start):
        bw_info = BwInfo('exchange', 'queue', 'routing_key', 'method')
        self.assertTrue(mock_thread_start.called)

    @mock.patch('registry.dynamic_policies.metrics.swift_metric.SwiftMetric._send_data_to_logstash')
    def test_metrics_swift_metric(self, mock_send_data_to_logstash):
        swift_metric = SwiftMetric('exchange', 'metric_id', 'routing_key')
        data = {"controller": {"@timestamp": 123456789, "AUTH_bd34c4073b65426894545b36f0d8dcce": 3}}
        body = json.dumps(data)
        swift_metric.notify(body)
        self.assertTrue(mock_send_data_to_logstash.called)

    #
    # Aux methods
    #

    def setup_dsl_parser_data(self):
        self.r.hmset('dsl_filter:compression', {'activation_url': 'http://example.com/filters',
                                                'identifier': '1',
                                                'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'})
        self.r.hmset('dsl_filter:encryption', {'activation_url': 'http://example.com/filters',
                                               'identifier': '2',
                                               'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})