import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from metrics.views import metric_module_list, metric_module_detail, MetricModuleData, list_activated_metrics


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class MetricsTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.factory = APIRequestFactory()
        self.create_metric_modules()

    def tearDown(self):
        self.r.flushdb()

    #
    # Metric module tests
    #

    def test_metric_module_list_with_method_not_allowed(self):
        # No post for metric module
        request = self.factory.post('/metrics')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_metric_modules_ok(self):
        request = self.factory.get('/metrics')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['metric_name'], 'm1.py')

    def test_metric_module_detail_with_method_not_allowed(self):
        request = self.factory.put('/metrics')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_metric_module_detail_ok(self):
        metric_id = '1'
        request = self.factory.get('/metrics/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'm1.py')

    def test_update_metric_module_detail_ok(self):
        metric_id = '1'
        data = {'status': 'Stopped'}
        request = self.factory.post('/metrics/' + metric_id, data, format='json')
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check the metric_module has been updated
        request = self.factory.get('/metrics/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['status'], 'Stopped')

    def test_delete_metric_module_detail_ok(self):
        metric_id = '1'
        request = self.factory.delete('/metrics/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check the metric module has been deleted
        request = self.factory.get('/metrics')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 0)

    def test_metric_module_data_view_with_method_not_allowed(self):
        # No DELETE method for this API call
        request = self.factory.delete('/metrics/data/')
        response = MetricModuleData.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('metrics.views.rsync_dir_with_nodes')
    def test_create_metric_module_ok(self, mock_rsync_dir):
        with open('test_data/test.py', 'r') as fp:
            metadata = {'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': False,
                        'in_flow': False, 'status': 'Stopped'}
            request = self.factory.post('/metrics/data/', {'file': fp, 'metadata': json.dumps(metadata)})
            response = MetricModuleData.as_view()(request)
            mock_rsync_dir.assert_called_with(settings.WORKLOAD_METRICS_DIR, settings.WORKLOAD_METRICS_DIR)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        metric = json.loads(response.content)
        self.assertEqual(metric['id'], 2)
        self.assertEqual(metric['metric_name'], 'test.py')
        self.assertEqual(metric['execution_server'], 'proxy')

        # check the metric module has been created
        metric_id = '2'
        request = self.factory.get('/metrics/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'test.py')

    @mock.patch('metrics.views.rsync_dir_with_nodes')
    def test_update_metric_module_put_ok(self, mock_rsync_dir):
        metric_id = '1'
        with open('test_data/test.py', 'r') as fp:
            request = self.factory.put('/metrics/' + metric_id + '/data', {'file': fp})
            response = MetricModuleData.as_view()(request, metric_id)
            mock_rsync_dir.assert_called_with(settings.WORKLOAD_METRICS_DIR, settings.WORKLOAD_METRICS_DIR)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check the metric module has been updated
        request = self.factory.get('/metrics/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'test.py')

    @mock.patch('metrics.views.os.path.join')
    def test_download_metric_module_get_ok(self, mock_os_path_join):
        mock_os_path_join.return_value = 'test_data/test.py'
        metric_id = '1'

        request = self.factory.get('/metrics/' + metric_id + '/data')
        response = MetricModuleData.as_view()(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Length'], '11')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=test.py')

    def test_download_metric_module_not_found(self):
        metric_id = '1'
        request = self.factory.get('/metrics/' + metric_id + '/data')
        response = MetricModuleData.as_view()(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_activated_metrics(self):
        self.setup_activated_metrics_data()
        request = self.factory.get('/metrics/activated')
        response = list_activated_metrics(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics_data = json.loads(response.content)
        self.assertEqual(len(metrics_data), 2)

    #
    # Aux methods
    #

    def create_metric_modules(self):
        self.r.incr("workload_metrics:id")  # setting autoincrement to 1
        # self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': 'False',
        #                                   'in_flow': 'False', 'status': 'Running', 'id': '1'})
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'status': 'Running', 'get': 'False', 'put': 'False',
                                           'execution_server': 'object', 'replicate': 'True', 'ssync': 'True', 'id': '1'})

    def setup_activated_metrics_data(self):
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
