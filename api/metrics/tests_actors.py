import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from metrics.views import metric_module_list, metric_module_detail, MetricModuleData, list_activated_metrics
from metrics.actors.swift_metric import SwiftMetric


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class MetricsActorsTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.factory = APIRequestFactory()
        self.create_metric_modules()

    def tearDown(self):
        self.r.flushdb()

    #
    # Actors
    #

    @mock.patch('metrics.actors.swift_metric.SwiftMetric._send_data_to_logstash')
    @mock.patch('metrics.actors.swift_metric.Thread')
    def test_swift_metric(self, mock_thread, mock_send_data_to_logstash):
        actor_id = '1'
        routing_key = 'metric.' + actor_id
        swift_metric = SwiftMetric(actor_id, routing_key)
        mock_thread.assert_called()
        mock_thread.return_value.start.assert_called()
        self.assertEqual(swift_metric.name, actor_id)

        body = '{"container": "crystal/data", "metric_name": "bandwidth", "@timestamp": "2017-09-09T18:00:18.331492+02:00", ' \
               '"value": 16.4375, "project": "crystal", "host": "controller", "method": "GET", "server_type": "proxy"}'
        swift_metric.notify(body)
        expected_dict = {'project': 'crystal', 'host': 'controller', 'container': 'crystal/data', 'metric_name': 'bandwidth',
                         'server_type': 'proxy', '@timestamp': '2017-09-09T18:00:18.331492+02:00', 'method': 'GET', 'value': 16.4375}
        mock_send_data_to_logstash.assert_called_with(expected_dict)
        self.assertFalse(swift_metric.metrics.empty())
        self.assertEqual(swift_metric.metrics.get(), expected_dict)

    #
    # Aux methods
    #

    def create_metric_modules(self):
        self.r.incr("workload_metrics:id")  # setting autoincrement to 1
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'status': 'Running', 'get': 'False', 'put': 'False',
                                           'execution_server': 'object', 'replicate': 'True', 'ssync': 'True', 'id': '1'})

    def setup_activated_metrics_data(self):
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
