import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from pyparsing import ParseException
from rest_framework import status
from rest_framework.test import APIRequestFactory

from filters.views import filter_list, filter_deploy, FilterData
from .dsl_parser import parse
from .views import object_type_list, object_type_detail, add_tenants_group, tenants_group_detail, gtenants_tenant_detail, \
    add_metric, metric_detail, metric_module_list, metric_module_detail, MetricModuleData, add_dynamic_filter, \
    dynamic_filter_detail, load_metrics, load_policies, static_policy_detail, dynamic_policy_detail, global_controller_list, global_controller_detail, \
    GlobalControllerData
from .views import policy_list


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class ControllerTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.factory = APIRequestFactory()
        self.create_storlet()
        self.upload_filter()
        self.deploy_storlet()
        self.create_object_type_docs()
        self.create_tenant_group_1()
        self.create_nodes()
        self.create_storage_nodes()
        self.create_metric_modules()
        self.create_global_controllers()

    def tearDown(self):
        self.r.flushdb()

    #
    # Static policy tests
    #

    @mock.patch('controller.views.get_project_list')
    def test_registry_static_policy(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/controller/static_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data[0]["target_name"], 'tenantA')

    def test_registry_dynamic_policy(self):
        # Create an instance of a GET request.
        request = self.factory.get('/controller/dynamic_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)  # is empty

    @mock.patch('controller.views.deploy_static_policy')
    def test_registry_static_policy_create_ok(self, mock_deploy_static_policy):
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef DO SET compression"
        request = self.factory.post('/controller/static_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_deploy_static_policy.called)

    @mock.patch('controller.views.get_project_list')
    @mock.patch('controller.views.set_filter')
    def test_registry_static_policy_create_set_filter_ok(self, mock_set_filter, mock_get_project_list):
        self.setup_dsl_parser_data()

        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef DO SET compression WITH bw=2 ON PROXY TO OBJECT_TYPE=DOCS"
        request = self.factory.post('/controller/static_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_set_filter.called)
        expected_policy_data = {'object_size': '', 'execution_order': 2, 'object_type': 'DOCS', 'params': mock.ANY, 'policy_id': 2, 'execution_server': 'PROXY', 'callable': False}
        mock_set_filter.assert_called_with(mock.ANY, '0123456789abcdef', mock.ANY, expected_policy_data, 'fake_token')

    @mock.patch('controller.views.deploy_dynamic_policy')
    def test_registry_dynamic_policy_create_ok(self, mock_deploy_dynamic_policy):
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/controller/dynamic_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_deploy_dynamic_policy.called)

    @mock.patch('controller.views.get_project_list')
    @mock.patch('controller.views.create_local_host')
    def test_registry_dynamic_policy_create_spawn_ok(self, mock_create_local_host, mock_get_project_list):
        self.setup_dsl_parser_data()

        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/controller/dynamic_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_create_local_host.called)
        self.assertTrue(mock_create_local_host.return_value.spawn.called)
        self.assertTrue(self.r.exists('policy:2'))
        policy_data = self.r.hgetall('policy:2')
        self.assertEqual(policy_data['policy'], 'FOR TENANT:0123456789abcdef WHEN metric1 > 5 DO SET compression')
        self.assertEqual(policy_data['condition'], 'metric1 > 5')

    # def test_registry_static_policy_create_with_inexistent_filter(self):
    #     self.setup_dsl_parser_data()
    #     self.r.delete("filter:1") # delete filter to cause an exception
    #
    #     # Create an instance of a POST request.
    #     data = "FOR TENANT:0123456789abcdef DO SET compression"
    #     request = self.factory.post('/controller/static_policy', data, content_type='text/plain')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
    #     response = policy_list(request)
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #
    # Metric tests
    #

    def test_list_metrics_ok(self):
        self.setup_dsl_parser_data()
        request = self.factory.get('/controller/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 2)

    def test_create_metric_ok(self):
        self.setup_dsl_parser_data()
        data = {'name': 'metric3', 'network_location': '?', 'type': 'integer'}
        request = self.factory.post('/controller/metrics', data, format='json')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert metric was created successfully
        request = self.factory.get('/controller/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 3)

    def test_get_metric_ok(self):
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        request = self.factory.get('/controller/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['type'], 'integer')

    def test_update_metric_ok(self):
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        data = {'network_location': '?', 'type': 'float'}
        request = self.factory.put('/controller/metrics/' + metric_name, data, format='json')
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert metric was updated successfully
        request = self.factory.get('/controller/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['type'], 'float')

    def test_delete_metric_ok(self):
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        request = self.factory.delete('/controller/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert metric was deleted successfully
        request = self.factory.get('/controller/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 1)

    #
    # Metric module tests
    #

    def test_metric_module_list_with_method_not_allowed(self):
        # No post for metric module
        request = self.factory.post('/controller/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_metric_modules_ok(self):
        request = self.factory.get('/controller/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['metric_name'], 'm1.py')

    def test_metric_module_detail_with_method_not_allowed(self):
        request = self.factory.put('/controller/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_metric_module_detail_ok(self):
        metric_id = '1'
        request = self.factory.get('/controller/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'm1.py')

    def test_update_metric_module_detail_ok(self):
        metric_id = '1'
        data = {'enabled': False}
        request = self.factory.post('/controller/metric_module/' + metric_id, data, format='json')
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check the metric_module has been updated
        request = self.factory.get('/controller/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['enabled'], False)

    def test_delete_metric_module_detail_ok(self):
        metric_id = '1'
        request = self.factory.delete('/controller/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check the metric module has been deleted
        request = self.factory.get('/controller/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 0)

    def test_metric_module_data_view_with_method_not_allowed(self):
        # No POST method for this API call
        request = self.factory.post('/controller/metric_module/data/')
        response = MetricModuleData.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('controller.views.rsync_dir_with_nodes')
    def test_create_metric_module_ok(self, mock_rsync_dir):
        with open('test_data/test.py', 'r') as fp:
            metadata = {'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': False,
                        'in_flow': False, 'enabled': False}
            request = self.factory.put('/controller/metric_module/data/', {'file': fp, 'metadata': json.dumps(metadata)})
            response = MetricModuleData.as_view()(request)
            mock_rsync_dir.assert_called_with(settings.WORKLOAD_METRICS_DIR)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        metric = json.loads(response.content)
        self.assertEqual(metric['id'], 2)
        self.assertEqual(metric['metric_name'], 'test.py')
        self.assertEqual(metric['execution_server'], 'proxy')

        # check the metric module has been created
        metric_id = '2'
        request = self.factory.get('/controller/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'test.py')

    #
    # DSL Filters tests
    #

    def test_add_dynamic_filter_with_method_not_allowed(self):
        # No DELETE method for this API call
        request = self.factory.delete('/controller/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_all_dsl_filters_ok(self):
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        request = self.factory.get('/controller/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 2)
        sorted_list = sorted(dsl_filters, key=lambda dslf: dslf['name'])
        self.assertEqual(sorted_list[0]['name'], 'compression')
        self.assertEqual(sorted_list[1]['name'], 'encryption')

    def test_create_dsl_filter_ok(self):
        data = {'name': 'caching', 'identifier': 'caching-1.0.jar', 'activation_url': 'http://localhost:7000/caching', 'valid_parameters': ''}
        request = self.factory.post('/controller/filters', data, format='json')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the DSL filter has been created successfully
        request = self.factory.get('/controller/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 1)
        self.assertEqual(dsl_filters[0]['name'], 'caching')

    def test_dynamic_filter_detail_with_method_not_allowed(self):
        # No POST method for this API call
        request = self.factory.post('/controller/filters/dummy', {'activation_url': 'http://www.example.com'}, format='json')
        response = dynamic_filter_detail(request, 'dummy')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_dsl_filter_ok(self):
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        request = self.factory.get('/controller/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filter = json.loads(response.content)
        valid_parameters = json.loads(dsl_filter['valid_parameters'])
        self.assertEqual(len(valid_parameters), 3)
        self.assertEqual(valid_parameters['eparam1'], 'integer')

    def test_update_dsl_filter_ok(self):
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        data = {'activation_url': 'http://www.example.com/encryption'}
        request = self.factory.put('/controller/filters/' + dsl_filter_name, data, format='json')
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the DSL filter has been updated successfully
        request = self.factory.get('/controller/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filter = json.loads(response.content)
        self.assertEqual(dsl_filter['activation_url'], data['activation_url'])

    def test_update_dsl_filter_with_non_existent_name(self):
        dsl_filter_name = 'unknown'
        data = {'activation_url': 'http://www.example.com'}
        request = self.factory.put('/controller/filters/' + dsl_filter_name, data, format='json')
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_dsl_filter_ok(self):
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        request = self.factory.delete('/controller/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the DSL filter has been deleted successfully
        request = self.factory.get('/controller/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 1)

    #
    # object_type tests
    #

    def test_object_type_list_with_method_not_allowed(self):
        request = self.factory.delete('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_object_type_detail_with_method_not_allowed(self):
        name = 'AUDIO'
        object_type_data = {'name': name, 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/controller/object_type/' + name, object_type_data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_object_types_ok(self):
        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        object_types = json.loads(response.content)

        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 3)

    def test_create_object_type_ok(self):
        # Create a second object type:
        object_type_data = {'name': 'VIDEO', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # obtain the list
        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 2)

    def test_create_object_type_without_name(self):
        # Create a second object type without name --> ERROR
        object_type_data = {'types_list': ['avi', 'mkv']}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_an_existing_name(self):
        # Create a second object type with an existing name --> ERROR
        object_type_data = {'name': 'DOCS', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_without_types_list(self):
        # Create a second object type without_types_list --> ERROR
        object_type_data = {'name': 'VIDEO'}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_empty_types_list(self):
        # Create a second object type with empty types_list --> ERROR
        object_type_data = {'name': 'VIDEO', 'types_list': []}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_object_type_detail_ok(self):
        name = 'DOCS'
        request = self.factory.get('/controller/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        object_type = json.loads(response.content)
        self.assertEqual(object_type['name'], name)
        self.assertEqual(len(object_type['types_list']), 3)
        self.assertTrue('txt' in object_type['types_list'])

    def test_object_type_detail_with_non_existent_name(self):
        name = 'AUDIO'
        request = self.factory.get('/controller/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_object_type_ok(self):
        name = 'DOCS'
        request = self.factory.delete('/controller/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_object_type_with_non_existent_name(self):
        name = 'AUDIO'
        request = self.factory.delete('/controller/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(object_types[0]['name'], "DOCS")

    def test_update_object_type_ok(self):
        name = 'DOCS'
        data = ['txt', 'doc']
        request = self.factory.put('/controller/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 1)
        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 2)
        self.assertTrue(data[0] in object_types[0]['types_list'])
        self.assertTrue(data[1] in object_types[0]['types_list'])

    def test_update_object_type_ok_with_more_extensions(self):
        name = 'DOCS'
        data = ['txt', 'doc', 'docx', 'odt']
        request = self.factory.put('/controller/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/controller/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 1)
        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 4)
        for extension in data:
            self.assertTrue(extension in object_types[0]['types_list'])

    def test_update_object_type_with_non_existent_name(self):
        name = 'VIDEO'
        data = ['avi', 'mkv']
        request = self.factory.put('/controller/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_object_type_with_empty_list(self):
        # It's wrong to send an empty list
        name = 'DOCS'
        data = []
        request = self.factory.put('/controller/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # TODO Add tests for object_type_items_detail()

    #
    # Tenant groups
    #

    def test_add_tenants_group_with_method_not_allowed(self):
        request = self.factory.delete('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_tenants_group_detail_with_method_not_allowed(self):
        gtenant_id = 1
        tenants = ['0123456789abcdf', 'abcdef0123456789']
        request = self.factory.post('/controller/gtenants/' + str(gtenant_id), tenants, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gtenants_tenant_detail_with_method_not_allowed(self):
        gtenant_id = '1'
        tenant_id = '0123456789abcdef'
        request = self.factory.get('/controller/gtenants/' + gtenant_id + '/tenants/' + tenant_id)
        response = gtenants_tenant_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_tenants_group_ok(self):
        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 2)  # 2 tenants in the group
        self.assertTrue('0123456789abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef0123456789' in tenants_groups['1'])

    def test_create_tenant_group_ok(self):
        # Create a second tenant group
        tenant_group_data = ['tenant1_id', 'tenant2_id', 'tenant3_id']
        request = self.factory.post('/controller/gtenants', tenant_group_data, format='json')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 2)  # 2 groups
        self.assertEqual(len(tenants_groups['2']), 3)  # 3 tenants in the 2nd group
        self.assertTrue('tenant1_id' in tenants_groups['2'])
        self.assertTrue('tenant2_id' in tenants_groups['2'])
        self.assertTrue('tenant3_id' in tenants_groups['2'])
        self.assertFalse('0123456789abcdef' in tenants_groups['2'])

    def test_create_tenant_group_with_empty_data(self):
        # Create a second tenant group with empty data --> ERROR
        tenant_group_data = []
        request = self.factory.post('/controller/gtenants', tenant_group_data, format='json')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_group_detail_ok(self):
        gtenant_id = '1'
        request = self.factory.get('/controller/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenant_list = json.loads(response.content)
        self.assertEqual(len(tenant_list), 2)
        self.assertTrue('0123456789abcdef' in tenant_list)
        self.assertTrue('abcdef0123456789' in tenant_list)

    def test_tenant_group_detail_with_non_existent_id(self):
        gtenant_id = '2'
        request = self.factory.get('/controller/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_tenant_group_ok(self):
        gtenant_id = '1'
        request = self.factory.delete('/controller/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "{}")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 0)

    def test_delete_tenant_group_with_non_existent_id(self):
        gtenant_id = '2'
        request = self.factory.delete('/controller/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "{}")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 2)  # 2 tenants in the group

    def test_update_tenant_group_ok(self):
        gtenant_id = '1'
        data = ['0123456789abcdef', 'abcdef0123456789', '3333333333']
        request = self.factory.put('/controller/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 3)  # 2 tenants in the group
        self.assertTrue('0123456789abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef0123456789' in tenants_groups['1'])
        self.assertTrue('3333333333' in tenants_groups['1'])

    def test_update_tenant_group_with_non_existent_id(self):
        gtenant_id = '2'
        data = ['0123456789abcdef', 'abcdef0123456789', '3333333333']
        request = self.factory.put('/controller/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_tenant_group_with_empty_data(self):
        gtenant_id = '1'
        data = []
        request = self.factory.put('/controller/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_individual_tenant_from_group_ok(self):
        gtenant_id = '1'
        tenant_id = '0123456789abcdef'
        request = self.factory.delete('/controller/gtenants/' + gtenant_id + '/tenants/' + tenant_id)
        response = gtenants_tenant_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check delete was successful
        request = self.factory.get('/controller/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)
        self.assertEqual(len(tenants_groups['1']), 1)
        self.assertFalse('0123456789abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef0123456789' in tenants_groups['1'])

    #
    # Parse tests
    #

    # To test dsl_parser correctly, we need to have metrics and filters in Redis.

    def test_parse_target_tenant_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(action_list), 1)
        target = targets[0]
        self.assertEqual(target.type, 'TENANT')
        self.assertEqual(target[1], '0123456789abcdef')
        action_info = action_list[0]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'compression')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(action_info.params, '')

    def test_parse_target_container_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR CONTAINER:0123456789abcdef/container1 DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'CONTAINER')
        self.assertEqual(target[1], '0123456789abcdef/container1')

    def test_parse_target_object_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR OBJECT:0123456789abcdef/container1/object.txt DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'OBJECT')
        self.assertEqual(target[1], '0123456789abcdef/container1/object.txt')

    def test_parse_target_tenant_2_actions_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression, SET encryption')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(action_list), 2)
        action_info = action_list[0]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'compression')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(action_info.params, '')
        action_info = action_list[1]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'encryption')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(action_info.params, '')

    def test_parse_target_tenant_to_object_type_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression TO OBJECT_TYPE=DOCS')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        object_list = rule_parsed.object_list
        self.assertIsNotNone(object_list)
        object_type = object_list.object_type
        self.assertIsNotNone(object_type)
        self.assertIsNotNone(object_type.object_value)
        self.assertEqual(object_type.object_value, 'DOCS')

    def test_parse_target_tenant_with_parameters_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression WITH cparam1=11, cparam2=12, cparam3=13')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(action_list), 1)
        action_info = action_list[0]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'compression')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(len(action_info.params), 6)  # ???

    def test_parse_group_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR G:1 DO SET compression')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 2)
        self.assertEqual(len(action_list), 1)
        self.assertEqual(targets[0], 'abcdef0123456789')
        self.assertEqual(targets[1], '0123456789abcdef')

    def test_parse_rule_not_starting_with_for(self):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('TENANT:1234 DO SET compression')

    def test_parse_rule_with_invalid_target(self):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('FOR xxxxxxx DO SET compression')

    def test_parse_callable_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression CALLABLE')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(action_list), 1)
        target = targets[0]
        self.assertEqual(target.type, 'TENANT')
        self.assertEqual(target[1], '0123456789abcdef')
        action_info = action_list[0]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'compression')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(action_info.params, '')
        self.assertEqual(action_info.callable, 'CALLABLE')

    def test_parse_not_callable(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:0123456789abcdef DO SET compression')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        action_list = rule_parsed.action_list
        self.assertEqual(len(action_list), 1)
        action_info = action_list[0]
        self.assertEqual(action_info.callable, '')

    # TODO Add tests with wrong number of parameters, non existent parameters, wrong type parameters, ...
    # TODO Add tests for conditional rules

    #
    # load_metrics() / load_policies()
    #

    @mock.patch('controller.views.start_metric')
    def test_load_metrics(self, mock_start_metric):
        load_metrics()
        mock_start_metric.assert_called_with(1, 'm1')

    @mock.patch('controller.views.create_local_host')
    def test_load_policies_not_alive(self, mock_create_local_host):
        self.r.hmset('policy:20',
                     {'alive': 'False', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression'})
        load_policies()
        self.assertEqual(len(mock_create_local_host.return_value.method_calls), 0)

    @mock.patch('controller.views.create_local_host')
    def test_load_policies_alive(self, mock_create_local_host):
        self.setup_dsl_parser_data()
        self.r.hmset('policy:21',
                     {'alive': 'True', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression'})
        load_policies()
        self.assertTrue(mock_create_local_host.return_value.spawn.called)

    @mock.patch('controller.views.create_local_host')
    def test_load_policies_alive_transient(self, mock_create_local_host):
        self.setup_dsl_parser_data()
        self.r.hmset('policy:21',
                     {'alive': 'True', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression TRANSIENT'})
        load_policies()
        self.assertTrue(mock_create_local_host.return_value.spawn.called)

    #
    # static_policy_detail()
    #

    @mock.patch('controller.views.get_project_list')
    def test_registry_static_policy_detail_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/controller/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["target_name"], 'tenantA')

    @mock.patch('controller.views.get_project_list')
    def test_registry_static_policy_update(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a PUT request.
        data = {"execution_server": "object", "execution_server_reverse": "object"}
        request = self.factory.put('/controller/static_policy/0123456789abcdef:1', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create an instance of a GET request.
        request = self.factory.get('/controller/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["execution_server"], 'object')
        self.assertEqual(json_data["execution_server_reverse"], 'object')

    @mock.patch('controller.views.get_project_list')
    def test_registry_static_policy_detail_delete(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a DELETE request.
        request = self.factory.delete('/controller/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check there is no policy
        request = self.factory.get('/controller/static_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)

    #
    # dynamic_policy_detail()
    #

    def test_registry_dynamic_policy_detail_with_method_not_allowed(self):
        request = self.factory.get('/controller/dynamic_policy/123')
        response = dynamic_policy_detail(request, '123')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    #
    # global_controller_list()/global_controller_detail()
    #

    def test_global_controller_list_with_method_not_allowed(self):
        request = self.factory.delete('/controller/global_controllers')
        response = global_controller_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_global_controller_detail_with_method_not_allowed(self):
        gc_id = '1'
        request = self.factory.post('/controller/global_controller/' + gc_id)
        response = global_controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # def test_object_type_detail_with_method_not_allowed(self):
    #     name = 'AUDIO'
    #     object_type_data = {'name': name, 'types_list': ['avi', 'mkv']}
    #     request = self.factory.post('/controller/object_type/' + name, object_type_data, format='json')
    #     response = object_type_detail(request, name)
    #     self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_global_controller_list_ok(self):
        request = self.factory.get('/controller/global_controllers')
        response = global_controller_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        global_controllers = json.loads(response.content)
        self.assertEqual(global_controllers[0]['class_name'], "MinTenantSLOGlobalSpareBWShare")

    def test_global_controller_detail_get_ok(self):
        gc_id = '1'
        request = self.factory.get('/controller/global_controller/' + gc_id)
        response = global_controller_detail(request, gc_id)

        global_controller = json.loads(response.content)
        self.assertEqual(global_controller['class_name'], "MinTenantSLOGlobalSpareBWShare")
        self.assertEqual(global_controller['enabled'], False)

    def test_global_controller_detail_delete_ok(self):
        gc_id = '1'
        request = self.factory.delete('/controller/global_controller/' + gc_id)
        response = global_controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify controller is deleted
        request = self.factory.get('/controller/global_controllers')
        response = global_controller_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        global_controllers = json.loads(response.content)
        self.assertEqual(len(global_controllers), 0)

    @mock.patch('controller.views.stop_global_controller')
    @mock.patch('controller.views.start_global_controller')
    def test_global_controller_detail_update_start_stop_ok(self, mock_start_global_controller, mock_stop_global_controller):
        gc_id = '1'
        controller_data = {'enabled': 'True'}
        request = self.factory.put('/controller/global_controller/' + gc_id, controller_data, format='json')
        response = global_controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_start_global_controller.called)

        controller_data = {'enabled': 'False'}
        request = self.factory.put('/controller/global_controller/' + gc_id, controller_data, format='json')
        response = global_controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_stop_global_controller.called)

    def test_global_controller_data_view_with_method_not_allowed(self):
        # No PUT method for this API call
        request = self.factory.put('/controller/global_controllers/data/')
        response = GlobalControllerData.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('controller.views.start_global_controller')
    def test_create_global_controller_ok(self, mock_start_global_controller):
        with open('test_data/test.py', 'r') as fp:
            metadata = {'class_name': 'TestClass', 'enabled': True, 'dsl_filter': 'test_filter', 'type': 'get'}
            request = self.factory.post('/controller/global_controllers/data/', {'file': fp, 'metadata': json.dumps(metadata)})
            response = GlobalControllerData.as_view()(request)

        mock_start_global_controller.assert_called_with('2', 'test', 'TestClass', 'get', 'test_filter')
        #self.assertTrue(mock_start_global_controller.called)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        global_controller = json.loads(response.content)
        self.assertEqual(global_controller['id'], 2)
        self.assertEqual(global_controller['enabled'], True)
        self.assertEqual(global_controller['controller_name'], 'test.py')

        # check the global controller has been created
        gc_id = '2'
        request = self.factory.get('/controller/global_controller/' + gc_id)
        response = global_controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gc_data = json.loads(response.content)
        self.assertEqual(gc_data['controller_name'], 'test.py')

    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'filter_type': 'storlet', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_pre_put': 'False', 'is_post_get': 'False',
                       'is_post_put': 'False', 'is_pre_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def upload_filter(self):
        # Upload a filter for the storlet 1
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            FilterData.as_view()(request, 1)

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('controller.views.get_project_list')
    @mock.patch('filters.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def deploy_storlet(self, mock_put_object, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # mock_requests_get.return_value = self.keystone_get_tenants_response()
        # mock_get_crystal_token.return_value = settings.SWIFT_URL + settings.SWIFT_API_VERSION + '/AUTH_0123456789abcdef', 'fake_token'

        # Call filter_deploy
        policy_data = {
            "policy_id": "1",
            "object_type": None,
            "object_size": None,
            "execution_order": "1",
            "params": ""
        }
        request = self.factory.put('/0123456789abcdef/deploy/1', policy_data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = filter_deploy(request, "1", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_object_type_docs(self):
        object_type_data = {'name': 'DOCS', 'types_list': ['txt', 'doc', 'docx']}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def setup_dsl_parser_data(self):
        self.r.hmset('dsl_filter:compression', {'identifier': '1', 'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}',
                                                'activation_url': 'http://10.30.1.6:9000/filters'})
        self.r.hmset('dsl_filter:encryption', {'identifier': '2', 'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}',
                                               'activation_url': 'http://10.30.1.6:9000/filters'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
        self.r.rpush('G:1', '0123456789abcdef')
        self.r.rpush('G:2', 'abcdef0123456789')

    def create_tenant_group_1(self):
        tenant_group_data = ['0123456789abcdef', 'abcdef0123456789']
        request = self.factory.post('/controller/gtenants', tenant_group_data, format='json')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_nodes(self):
        self.r.hmset('node:controller',
                     {'ip': '192.168.2.1', 'last_ping': '1467623304.332646', 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})

    def create_storage_nodes(self):
        self.r.incr("storage_nodes:id")  # setting autoincrement to 1
        self.r.hmset('SN:1', {'name': 'storagenode1', 'location': 'r1z1-192.168.1.5:6000/sdb1', 'type': 'hdd'})

    def create_metric_modules(self):
        self.r.incr("workload_metrics:id")  # setting autoincrement to 1
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': 'False',
                                           'in_flow': 'False', 'enabled': 'True', 'id': '1'})

    def create_global_controllers(self):
        self.r.incr("controllers:id")  # setting autoincrement to 1
        self.r.hmset('controller:1', {'class_name': 'MinTenantSLOGlobalSpareBWShare', 'enabled': 'False',
                                      'controller_name': 'min_slo_tenant_global_share_spare_bw_v2.py',
                                      'dsl_filter': 'bandwidth', 'type': 'put', 'id': '1'})