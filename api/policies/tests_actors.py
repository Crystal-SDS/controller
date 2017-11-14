import json
import os
import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from httmock import urlmatch, HTTMock

from actors.rule import Rule
from actors.rule_transient import TransientRule
from .dsl_parser import parse


@urlmatch(netloc=r'(.*\.)?example\.com')
def example_mock_200(url, request):
    return {'status_code': 200, 'content': 'OK'}


@urlmatch(netloc=r'(.*\.)?example\.com')
def example_mock_400(url, request):
    return {'status_code': 400, 'content': 'Error'}


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"))
class PoliciesActorsTestCase(TestCase):

    def setUp(self):
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

    def tearDown(self):
        self.r.flushdb()

    #
    # rules/rule
    #

    # def test_get_target_ok(self):
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = Rule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     self.assertEqual(rule.get_target(), target_name)

    # @mock.patch('policies.actors.rule.Rule._do_action')
    # def test_action_is_not_triggered(self, mock_do_action):
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = Rule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     rule.update('metric1', 3)
    #     self.assertFalse(mock_do_action.called)

    # @mock.patch('actors.rule.Rule._do_action')
    # def test_action_is_triggered(self, mock_do_action):
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = Rule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     rule.update('metric1', 6)
    #     self.assertTrue(mock_do_action.called)

    # @mock.patch('policies.actors.rule.redis.StrictRedis.hgetall')
    # @mock.patch('policies.actors.rule.redis.StrictRedis.hset')
    # @mock.patch('policies.actors.rule.Rule._get_admin_token')
    # def test_action_set_is_triggered_deploy_200(self, mock_admin_token, mock_redis_hset, mock_redis_hgetall):
    #     mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
    #                                        'identifier': '1',
    #                                        'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = Rule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     rule.id = '10'
    #     with HTTMock(example_mock_200):
    #         rule.update('metric1', 6)
    #     self.assertTrue(mock_admin_token.called)
    #     self.assertTrue(mock_redis_hset.called)
    #     mock_redis_hset.assert_called_with('10', 'alive', False)

    # @mock.patch('policies.actors.rule.redis.StrictRedis.hgetall')
    # @mock.patch('policies.actors.rule.redis.StrictRedis.hset')
    # @mock.patch('policies.actors.rule.Rule._get_admin_token')
    # def test_action_set_is_triggered_deploy_400(self, mock_admin_token, mock_redis_hset, mock_redis_hgetall):
    #     mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
    #                                        'identifier': '1',
    #                                        'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = Rule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     rule.id = '10'
    #     with HTTMock(example_mock_400):
    #         rule.update('metric1', 6)
    #     self.assertTrue(mock_admin_token.called)
    #     self.assertFalse(mock_redis_hset.called)

    # @mock.patch('policies.actors.rule.redis.StrictRedis.hgetall')
    # @mock.patch('policies.actors.rule.Rule._get_admin_token')
    # @mock.patch('policies.actors.rule.Rule.stop_actor')
    # def test_action_delete_is_triggered_undeploy_200(self, mock_stop_actor, mock_admin_token, mock_redis_hgetall):
    #     mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
    #                                        'identifier': '1',
    #                                        'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     action = parsed_rule.action_list[0]
    #     action.action = 'DELETE'
    #     rule = Rule(parsed_rule, action, target_id, target_name)
    #     rule.id = '10'
    #     with HTTMock(example_mock_200):
    #         rule.update('metric1', 6)
    #     self.assertTrue(mock_admin_token.called)
    #     self.assertTrue(mock_stop_actor.called)

    #
    # rules/rule_transient
    #

    # @mock.patch('policies.actors.rule_transient.TransientRule.do_action')
    # def test_transient_action_is_triggered(self, mock_do_action):
    #     self.setup_dsl_parser_data()
    #     _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression TRANSIENT')
    #     target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     target_name = 'tenant1'
    #     rule = TransientRule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     rule.update('metric1', 6)
    #     self.assertTrue(mock_do_action.called)

    # @mock.patch('policies.actors.rule.redis.StrictRedis.hgetall')
    # @mock.patch('policies.actors.rule_transient.TransientRule._get_admin_token')
    # @mock.patch('policies.actors.rule_transient.TransientRule.id')
    # @mock.patch('policies.actors.rule_transient.requests.put')
    # @mock.patch('policies.actors.rule_transient.requests.delete')
    # def test_transient_action_set_is_triggered_200(self, mock_requests_delete, mock_requests_put, mock_admin_token, mock_redis_hgetall):
    #     mock_redis_hgetall.return_value = {'activation_url': 'http://example.com/filters',
    #                                        'identifier': '1',
    #                                        'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'}
    #     self.setup_dsl_parser_data()
    #     # _, parsed_rule = parse('FOR TENANT:4f0279da74ef4584a29dc72c835fe2c9 WHEN metric1 > 5 DO SET compression TRANSIENT')
    #     # target_id = '4f0279da74ef4584a29dc72c835fe2c9'
    #     # target_name = 'tenant1'
    #     # rule = TransientRule(parsed_rule, parsed_rule.action_list[0], target_id, target_name)
    #     policy_data = {"id": 1,
    #                    "target_id": '4f0279da74ef4584a29dc72c835fe2c9',  # or 123456789/container_name
    #                    "target_name": 'tenant1',
    #                    "filter": 'compression',
    #                    "parameters": '',
    #                    "action": 'SET',
    #                    "condition": 'metric1 > 5',
    #                    "object_type": '',
    #                    "object_size": '',
    #                    "object_tag": '',
    #                    "transient": True,
    #                    "policy_location": 'tcp://127.0.0.1:6899/policies.actors.rule_transient/TransientRule/policy:1',
    #                    "status": 'Alive'}
    #     rule = TransientRule(policy_data, 'example.com')
    #
    #     rule.start_rule()
    #     rule.update('metric1', 6)
    #     self.assertTrue(mock_requests_put.called)
    #     self.assertFalse(mock_requests_delete.called)
    #     mock_requests_put.reset_mock()
    #     mock_requests_delete.reset_mock()
    #     rule.static_policy_id = 'FAKE_ID'
    #     rule.update('metric1', 4)
    #     self.assertFalse(mock_requests_put.called)
    #     self.assertTrue(mock_requests_delete.called)

    #
    # metrics/bw_info
    #

    # @mock.patch('controller.dynamic_policies.metrics.bw_info.Thread.start')
    # def test_metrics_bw_info(self, mock_thread_start):
    #     bw_info = BwInfo('exchange', 'queue', 'routing_key', 'method')
    #     self.assertTrue(mock_thread_start.called)
    #     data = {"10.0.0.1": {"123456789abcedef" : {"1": {"sda1": "12"}}}}
    #     body = json.dumps(data)
    #     bw_info.notify(body)
    #     self.assertEquals(bw_info.count["123456789abcedef"]["10.0.0.1"]["1"]["sda1"], "12")
    #
    # @mock.patch('controller.dynamic_policies.metrics.bw_info.Thread.start')
    # def test_metrics_bw_info_write_experimental_results(self, mock_thread_start):
    #     bw_info = BwInfo('exchange', 'queue', 'routing_key', 'method')
    #     self.assertTrue(mock_thread_start.called)
    #     data = {"123456789abcedef": {"10.0.0.1": {"1": {"sda1": 1.3}}}}
    #     bw_info._write_experimental_results(data)  # noqa
    #     bw_info._write_experimental_results(data)  # noqa
    #     bw_info._write_experimental_results(data)  # noqa
    #     bw_info._write_experimental_results(data)  # noqa
    #     bw_info._write_experimental_results(data)  # noqa
    #     self.assertEqual(len(bw_info.last_bw_info), 5)
    #     bw_info._write_experimental_results(data)  # noqa
    #     self.assertEqual(len(bw_info.last_bw_info), 1)

    #
    # metrics/bw_info_ssync
    #

    # @mock.patch('controller.dynamic_policies.metrics.bw_info.Thread.start')
    # def test_metrics_bw_info_ssync(self, mock_thread_start):
    #     bw_info_ssync = BwInfoSSYNC('exchange', 'queue', 'routing_key', 'method')
    #     self.assertTrue(mock_thread_start.called)
    #     data = {"10.0.0.1": '4'}  # ?
    #     body = json.dumps(data)
    #     bw_info_ssync.notify(body)
    #     self.assertEquals(bw_info_ssync.count["10.0.0.1"], "4")
    #
    # @mock.patch('controller.dynamic_policies.metrics.bw_info.Thread.start')
    # def test_metrics_bw_info_ssync_write_experimental_results(self, mock_thread_start):
    #     bw_info_ssync = BwInfoSSYNC('exchange', 'queue', 'routing_key', 'method')
    #     self.assertTrue(mock_thread_start.called)
    #     res1 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 4}, 'source:2': {'dev1': 2, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     res2 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 6}, 'source:2': {'dev1': 3, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     res3 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 4}, 'source:2': {'dev1': 4, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     res4 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 6}, 'source:2': {'dev1': 5, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     res5 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 5}, 'source:2': {'dev1': 6, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     res6 = {'controller:2': {'source:1': {'dev1': 2, 'dev2': 6}, 'source:2': {'dev1': 8, 'dev2': 4}}, 'stnode1:1': {'src:3': {'dev4': 10}}}
    #     bw_info_ssync._write_experimental_results(res1)  # noqa
    #     bw_info_ssync._write_experimental_results(res2)  # noqa
    #     bw_info_ssync._write_experimental_results(res3)  # noqa
    #     bw_info_ssync._write_experimental_results(res4)  # noqa
    #     bw_info_ssync._write_experimental_results(res5)  # noqa
    #     self.assertEqual(len(bw_info_ssync.last_bw_info), 5)
    #     bw_info_ssync._write_experimental_results(res6)  # noqa
    #     self.assertEqual(len(bw_info_ssync.last_bw_info),1)

    #
    # metrics/swift_metric
    #

    # @mock.patch('controller.dynamic_policies.metrics.swift_metric.Thread')
    # @mock.patch('controller.dynamic_policies.metrics.swift_metric.socket.socket')
    # def test_metrics_swift_metric(self, mock_socket, mock_thread):
    #     swift_metric = SwiftMetric('exchange', 'metric_id', 'routing_key')
    #     #data = {"controller": {"@timestamp": 123456789, "AUTH_bd34c4073b65426894545b36f0d8dcce": 3}}
    #     data = {'container': 'crystal/data', 'metric_name': 'bandwidth', '@timestamp': '2017-09-09T18:00:18.331492+02:00',
    #             'value': 16.4375, 'project': 'crystal', 'host': 'controller', 'method': 'GET', 'server_type': 'proxy'}
    #     body = json.dumps(data)
    #     swift_metric.notify(body)
    #     self.assertTrue(mock_thread.called)
    #     self.assertTrue(mock_socket.called)
    #     self.assertTrue(mock_socket.return_value.sendto.called)

    #
    # rules/min_bandwidth_per_tenant
    #

    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_bandwidth_per_tenant(self, mock_pika):
    #     smin = SimpleMinBandwidthPerTenant('the_name', 'the_method')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'1': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-1-sdb1': 115.0}})
    #
    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_bandwidth_per_tenant_overloaded(self, mock_pika):
    #     self.r.set('SLO:bandwidth:put_bw:AUTH_1234567890abcdef#0', 130)
    #
    #     smin = SimpleMinBandwidthPerTenant('the_name', 'PUT')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'0': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-0-sdb1': 115.0}})

    #
    # rules/min_slo_tenant_global_share_spare_bw
    #

    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_tenant_slo_global_spare_bw_share(self, mock_pika):
    #     smin = MinTenantSLOGlobalSpareBWShare('the_name', 'the_method')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'1': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-1-sdb1': 100.0}})
    #
    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_tenant_slo_global_spare_bw_share_overloaded(self, mock_pika):
    #     self.r.set('SLO:bandwidth:put_bw:AUTH_1234567890abcdef#0', 120)
    #
    #     smin = MinTenantSLOGlobalSpareBWShare('the_name', 'PUT')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'0': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-0-sdb1': 100.0}})

    #
    # rules/min_slo_tenant_global_share_spare_bw_v2
    #

    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_tenant_slo_global_spare_bw_share_v2(self, mock_pika):
    #     self.r.set('SLO:bandwidth:put_bw:AUTH_1234567890abcdef#0', 50)
    #
    #     smin = MinTenantSLOGlobalSpareBWShareV2('the_name', 'PUT')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'0': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-0-sdb1': 70.0}})
    #
    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_min_tenant_slo_global_spare_bw_share_v2_overloaded(self, mock_pika):
    #     self.r.set('SLO:bandwidth:put_bw:AUTH_1234567890abcdef#0', 100)
    #
    #     smin = MinTenantSLOGlobalSpareBWShareV2('the_name', 'PUT')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'0': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-0-sdb1': 70.0}})

    #
    # rules/simple_proportional_bandwidth
    #

    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_simple_proportional_bandwidth_per_tenant(self, mock_pika):
    #     self.r.set('SLO:bandwidth:put_bw:AUTH_1234567890abcdef#0', 80)
    #
    #     smin = StaticBandwidthPerTenant('the_name', 'PUT')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'0': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21-0-sdb1': 80.0}})

    #
    # rules/simple_proportional_replication_bandwidth
    #

    # @mock.patch('controller.dynamic_policies.rules.base_global_controller.pika')
    # def test_simple_proportional_replication_bandwidth(self, mock_pika):
    #     self.r.set('SLO:bandwidth:ssync_bw:AUTH_1234567890abcdef#0', 80)
    #
    #     smin = StaticReplicationBandwidth('the_name', 'the_method')
    #     self.assertTrue(mock_pika.PlainCredentials.called)
    #     info = {'AUTH_1234567890abcdef': {'192.168.2.21': {'1': {u'sdb1': 655350.0}}}}
    #     computed = smin.compute_algorithm(info)
    #     self.assertEqual(computed, {'AUTH_1234567890abcdef': {'192.168.2.21': 80.0}})

    #
    # Aux methods
    #

    def setup_dsl_parser_data(self):
        # Simplified filter data:
        self.r.hmset('filter:compression', {'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'})
        self.r.hmset('filter:encryption', {'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})