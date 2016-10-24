import json
import mock
import os
import redis


from django.test import TestCase, override_settings
from django.conf import settings
from pyparsing import ParseException
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import policy_list
from filters.views import storlet_list, filter_deploy, StorletData
from .views import object_type_list, object_type_detail, add_tenants_group, tenants_group_detail, gtenants_tenant_detail, node_list, node_detail, \
    add_metric, metric_detail, metric_module_list, metric_module_detail, MetricModuleData, list_storage_node, storage_node_detail, add_dynamic_filter, \
    dynamic_filter_detail, load_metrics, load_policies, static_policy_detail, dynamic_policy_detail
from .dsl_parser import parse


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "native_metrics"))
@mock.patch('registry.views.is_valid_request')
class RegistryTestCase(TestCase):
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

    def tearDown(self):
        self.r.flushdb()

    #
    # Static policy tests
    #

    @mock.patch('registry.views.get_project_list')
    def test_registry_static_policy(self, mock_get_project_list, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/registry/static_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data[0]["target_name"], 'tenantA')

    def test_registry_static_policy_without_auth_token(self, mock_is_valid_request):
        mock_is_valid_request.return_value = False

        # Create an instance of a GET request without auth token
        request = self.factory.get('/registry/static_policy')
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registry_dynamic_policy(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'

        # Create an instance of a GET request.
        request = self.factory.get('/registry/dynamic_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)  # is empty

    @mock.patch('registry.views.do_action')
    def test_registry_static_policy_create_ok(self, mock_do_action, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:1234567890abcdef DO SET compression"
        request = self.factory.post('/registry/static_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_do_action.called)

    @mock.patch('registry.views.set_filter')
    def test_registry_static_policy_create_set_filter_ok(self, mock_set_filter, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:1234567890abcdef DO SET compression WITH bw=2 ON PROXY TO OBJECT_TYPE=DOCS"
        request = self.factory.post('/registry/static_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_set_filter.called)
        expected_policy_data = {'object_size': '', 'execution_order': 2, 'object_type': 'DOCS', 'params': mock.ANY, 'policy_id': 2, 'execution_server': 'PROXY'}
        mock_set_filter.assert_called_with(mock.ANY, '1234567890abcdef', mock.ANY, expected_policy_data, 'fake_token')

    @mock.patch('registry.views.deploy_policy')
    def test_registry_dynamic_policy_create_ok(self, mock_deploy_policy, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:1234567890abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/registry/dynamic_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_deploy_policy.called)

    @mock.patch('registry.views.host')
    @mock.patch('registry.views.create_local_host')
    def test_registry_dynamic_policy_create_spawn_id_ok(self, mock_create_local_host, mock_host, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:1234567890abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/registry/dynamic_policy', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_create_local_host.called)
        self.assertTrue(mock_host.spawn_id.called)
        self.assertTrue(self.r.exists('policy:2'))
        policy_data = self.r.hgetall('policy:2')
        self.assertEqual(policy_data['policy'], 'FOR TENANT:1234567890abcdef DO SET compression')
        self.assertEqual(policy_data['condition'], 'metric1 > 5')

    # def test_registry_static_policy_create_with_inexistent_filter(self, mock_is_valid_request):
    #     mock_is_valid_request.return_value = 'fake_token'
    #     self.setup_dsl_parser_data()
    #     self.r.delete("filter:1") # delete filter to cause an exception
    #
    #     # Create an instance of a POST request.
    #     data = "FOR TENANT:1234567890abcdef DO SET compression"
    #     request = self.factory.post('/registry/static_policy', data, content_type='text/plain')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
    #     response = policy_list(request)
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #
    # Metric tests
    #

    def test_list_metrics_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()
        request = self.factory.get('/registry/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 2)

    def test_create_metric_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()
        data = {'name': 'metric3', 'network_location': '?', 'type': 'integer'}
        request = self.factory.post('/registry/metrics', data, format='json')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert metric was created successfully
        request = self.factory.get('/registry/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 3)

    def test_get_metric_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        request = self.factory.get('/registry/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['type'], 'integer')

    def test_update_metric_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        data = {'network_location': '?', 'type': 'float'}
        request = self.factory.put('/registry/metrics/' + metric_name, data, format='json')
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert metric was updated successfully
        request = self.factory.get('/registry/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['type'], 'float')

    def test_delete_metric_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        self.setup_dsl_parser_data()
        metric_name = 'metric1'
        request = self.factory.delete('/registry/metrics/' + metric_name)
        response = metric_detail(request, metric_name)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert metric was deleted successfully
        request = self.factory.get('/registry/metrics')
        response = add_metric(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 1)

    #
    # Metric module tests
    #

    def test_metric_module_list_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # No post for metric module
        request = self.factory.post('/registry/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_metric_modules_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['metric_name'], 'm1.py')

    def test_metric_module_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.post('/registry/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_metric_module_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        metric_id = '1'
        request = self.factory.get('/registry/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'm1.py')

    def test_update_metric_module_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        metric_id = '1'
        data = {'execution_server': 'object', 'enabled': False}
        request = self.factory.put('/registry/metric_module/' + metric_id, data, format='json')
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check the metric_module has been updated
        request = self.factory.get('/registry/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['execution_server'], 'object')

    def test_delete_metric_module_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        metric_id = '1'
        request = self.factory.delete('/registry/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check the metric module has been deleted
        request = self.factory.get('/registry/metric_module')
        response = metric_module_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = json.loads(response.content)
        self.assertEqual(len(metrics), 0)

    def test_metric_module_data_view_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # No PUT method for this API call
        request = self.factory.put('/registry/metric_module/data/')
        response = MetricModuleData.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('registry.views.rsync_dir_with_nodes')
    def test_create_metric_module_ok(self, mock_rsync_dir, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        with open('test_data/test.py', 'r') as fp:
            metadata = {'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': False,
                        'in_flow': False, 'enabled': False}
            request = self.factory.post('/registry/metric_module/data/', {'file': fp, 'metadata': json.dumps(metadata)})
            response = MetricModuleData.as_view()(request)
            mock_rsync_dir.assert_called_with(settings.WORKLOAD_METRICS_DIR)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        metric = json.loads(response.content)
        self.assertEqual(metric['id'], 2)
        self.assertEqual(metric['metric_name'], 'test.py')
        self.assertEqual(metric['execution_server'], 'proxy')

        # check the metric module has been created
        metric_id = '2'
        request = self.factory.get('/registry/metric_module/' + metric_id)
        response = metric_module_detail(request, metric_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['metric_name'], 'test.py')



    #
    # DSL Filters tests
    #

    def test_add_dynamic_filter_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # No DELETE method for this API call
        request = self.factory.delete('/registry/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_all_dsl_filters_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        request = self.factory.get('/registry/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 2)
        sorted_list = sorted(dsl_filters, key=lambda dslf: dslf['name'])
        self.assertEqual(sorted_list[0]['name'], 'compression')
        self.assertEqual(sorted_list[1]['name'], 'encryption')

    def test_create_dsl_filter_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        data = {'name': 'caching', 'identifier': 'caching-1.0.jar', 'activation_url': 'http://localhost:7000/caching', 'valid_parameters': ''}
        request = self.factory.post('/registry/filters', data, format='json')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the DSL filter has been created successfully
        request = self.factory.get('/registry/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 1)
        self.assertEqual(dsl_filters[0]['name'], 'caching')

    def test_dynamic_filter_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # No POST method for this API call
        request = self.factory.post('/registry/filters/dummy', {'activation_url': 'http://www.example.com'}, format='json')
        response = dynamic_filter_detail(request, 'dummy')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_dsl_filter_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        request = self.factory.get('/registry/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filter = json.loads(response.content)
        valid_parameters = json.loads(dsl_filter['valid_parameters'])
        self.assertEqual(len(valid_parameters), 3)
        self.assertEqual(valid_parameters['eparam1'], 'integer')

    def test_update_dsl_filter_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        data = {'activation_url': 'http://www.example.com/encryption'}
        request = self.factory.put('/registry/filters/' + dsl_filter_name, data, format='json')
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the DSL filter has been updated successfully
        request = self.factory.get('/registry/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filter = json.loads(response.content)
        self.assertEqual(dsl_filter['activation_url'], data['activation_url'])

    def test_update_dsl_filter_with_non_existent_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        dsl_filter_name = 'unknown'
        data = {'activation_url': 'http://www.example.com'}
        request = self.factory.put('/registry/filters/' + dsl_filter_name, data, format='json')
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_dsl_filter_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create 2 dsl filters in redis
        self.setup_dsl_parser_data()

        dsl_filter_name = 'encryption'
        request = self.factory.delete('/registry/filters/' + dsl_filter_name)
        response = dynamic_filter_detail(request, dsl_filter_name)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the DSL filter has been deleted successfully
        request = self.factory.get('/registry/filters')
        response = add_dynamic_filter(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dsl_filters = json.loads(response.content)
        self.assertEqual(len(dsl_filters), 1)

    #
    # Storage nodes tests
    #

    def test_list_storage_nodes_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/snode')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_nodes = json.loads(response.content)
        self.assertEqual(len(storage_nodes), 1)

    def test_create_storage_node_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        data = {'name': 'storagenode2', 'location': 'location2', 'type': 'type2'}
        request = self.factory.post('/registry/snode', data, format='json')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert the storage node was created successfully
        request = self.factory.get('/registry/snode')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_nodes = json.loads(response.content)
        self.assertEqual(len(storage_nodes), 2)

    def test_list_storage_nodes_are_ordered_by_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Register a new SN
        data = {'name': 'storagenode3', 'location': 'location3', 'type': 'type3'}
        request = self.factory.post('/registry/snode', data, format='json')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Register a new SN
        data = {'name': 'storagenode2', 'location': 'location2', 'type': 'type2'}
        request = self.factory.post('/registry/snode', data, format='json')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Register a new SN
        data = {'name': 'storagenode4', 'location': 'location4', 'type': 'type4'}
        request = self.factory.post('/registry/snode', data, format='json')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert the storage nodes are returned ordered by name
        request = self.factory.get('/registry/snode')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_nodes = json.loads(response.content)
        self.assertEqual(len(storage_nodes), 4)
        self.assertEqual(storage_nodes[0]['name'], 'storagenode1')
        self.assertEqual(storage_nodes[1]['name'], 'storagenode2')
        self.assertEqual(storage_nodes[2]['name'], 'storagenode3')
        self.assertEqual(storage_nodes[3]['name'], 'storagenode4')

    def test_get_storage_node_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        snode_id = 1
        request = self.factory.get('/registry/snode/' + str(snode_id))
        response = storage_node_detail(request, str(snode_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['name'], 'storagenode1')
        self.assertEqual(metric_data['location'], 'r1z1-192.168.1.5:6000/sdb1')
        self.assertEqual(metric_data['type'], 'hdd')

    def test_update_storage_node_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        snode_id = 1
        data = {'name': 'storagenode1updated', 'location': 'r1z1-192.168.1.6:6000/sdb1', 'type': 'hddupdated'}
        request = self.factory.put('/registry/snode/' + str(snode_id), data, format='json')
        response = storage_node_detail(request, str(snode_id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # asserts it was modified successfully
        request = self.factory.get('/registry/snode/' + str(snode_id))
        response = storage_node_detail(request, str(snode_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metric_data = json.loads(response.content)
        self.assertEqual(metric_data['name'], 'storagenode1updated')
        self.assertEqual(metric_data['location'], 'r1z1-192.168.1.6:6000/sdb1')
        self.assertEqual(metric_data['type'], 'hddupdated')

    def test_delete_storage_node_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        snode_id = 1
        request = self.factory.delete('/registry/snode/' + str(snode_id))
        response = storage_node_detail(request, str(snode_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert it was deleted successfully
        request = self.factory.get('/registry/snode')
        response = list_storage_node(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_nodes = json.loads(response.content)
        self.assertEqual(len(storage_nodes), 0)

    #
    # object_type tests
    #

    def test_object_type_list_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.delete('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_object_type_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'AUDIO'
        object_type_data = {'name': name, 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type/' + name, object_type_data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_object_types_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        object_types = json.loads(response.content)

        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 3)

    def test_create_object_type_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second object type:
        object_type_data = {'name': 'VIDEO', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # obtain the list
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 2)

    def test_create_object_type_without_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second object type without name --> ERROR
        object_type_data = {'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_an_existing_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second object type with an existing name --> ERROR
        object_type_data = {'name': 'DOCS', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_without_types_list(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second object type without_types_list --> ERROR
        object_type_data = {'name': 'VIDEO'}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_empty_types_list(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second object type with empty types_list --> ERROR
        object_type_data = {'name': 'VIDEO', 'types_list': []}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_object_type_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'DOCS'
        request = self.factory.get('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        object_type = json.loads(response.content)
        self.assertEqual(object_type['name'], name)
        self.assertEqual(len(object_type['types_list']), 3)
        self.assertTrue('txt' in object_type['types_list'])

    def test_object_type_detail_with_non_existent_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'AUDIO'
        request = self.factory.get('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_object_type_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'DOCS'
        request = self.factory.delete('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_object_type_with_non_existent_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'AUDIO'
        request = self.factory.delete('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(object_types[0]['name'], "DOCS")

    def test_update_object_type_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'DOCS'
        data = ['txt', 'doc']
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 1)
        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 2)
        self.assertTrue(data[0] in object_types[0]['types_list'])
        self.assertTrue(data[1] in object_types[0]['types_list'])

    def test_update_object_type_ok_with_more_extensions(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        name = 'DOCS'
        data = ['txt', 'doc', 'docx', 'odt']
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 1)
        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 4)
        for extension in data:
            self.assertTrue(extension in object_types[0]['types_list'])

    def test_update_object_type_with_non_existent_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'

        name = 'VIDEO'
        data = ['avi', 'mkv']
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_object_type_with_empty_list(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # It's wrong to send an empty list
        name = 'DOCS'
        data = []
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # TODO Add tests for object_type_items_detail()

    #
    # Nodes
    #

    def test_node_list_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.delete('/registry/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_nodes_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        nodes = json.loads(response.content)
        self.assertEqual(len(nodes), 3)
        node_names = [node['name'] for node in nodes]
        self.assertTrue('controller' in node_names)
        self.assertTrue('storagenode1' in node_names)
        self.assertTrue('storagenode2' in node_names)
        a_device =  nodes[0]['devices'].keys()[0]
        self.assertIsNotNone(nodes[0]['devices'][a_device]['free'])

    def test_node_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        node_name = 'storagenode1'
        request = self.factory.delete('/registry/nodes/' + node_name)
        response = node_detail(request, node_name)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_node_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        node_name = 'storagenode1'
        request = self.factory.get('/registry/nodes/' + node_name)
        response = node_detail(request, node_name)
        node = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(node['name'], 'storagenode1')

    def test_get_node_detail_with_non_existent_node_name(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        node_name = 'storagenode1000'
        request = self.factory.get('/registry/nodes/' + node_name)
        response = node_detail(request, node_name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #
    # Tenant groups
    #

    def test_add_tenants_group_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.delete('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_tenants_group_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = 1
        tenants = ['1234567890abcdf', 'abcdef1234567890']
        request = self.factory.post('/registry/gtenants/' + str(gtenant_id), tenants, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gtenants_tenant_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        tenant_id = '1234567890abcdef'
        request = self.factory.get('/registry/gtenants/' + gtenant_id + '/tenants/' + tenant_id)
        response = gtenants_tenant_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_tenants_group_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 2)  # 2 tenants in the group
        self.assertTrue('1234567890abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef1234567890' in tenants_groups['1'])

    def test_create_tenant_group_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second tenant group
        tenant_group_data = ['tenant1_id', 'tenant2_id', 'tenant3_id']
        request = self.factory.post('/registry/gtenants', tenant_group_data, format='json')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 2)  # 2 groups
        self.assertEqual(len(tenants_groups['2']), 3)  # 3 tenants in the 2nd group
        self.assertTrue('tenant1_id' in tenants_groups['2'])
        self.assertTrue('tenant2_id' in tenants_groups['2'])
        self.assertTrue('tenant3_id' in tenants_groups['2'])
        self.assertFalse('1234567890abcdef' in tenants_groups['2'])

    def test_create_tenant_group_with_empty_data(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        # Create a second tenant group with empty data --> ERROR
        tenant_group_data = []
        request = self.factory.post('/registry/gtenants', tenant_group_data, format='json')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_group_detail_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        request = self.factory.get('/registry/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenant_list = json.loads(response.content)
        self.assertEqual(len(tenant_list), 2)
        self.assertTrue('1234567890abcdef' in tenant_list)
        self.assertTrue('abcdef1234567890' in tenant_list)

    def test_tenant_group_detail_with_non_existent_id(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '2'
        request = self.factory.get('/registry/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_tenant_group_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        request = self.factory.delete('/registry/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "{}")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 0)

    def test_delete_tenant_group_with_non_existent_id(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '2'
        request = self.factory.delete('/registry/gtenants/' + gtenant_id)
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "{}")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 2)  # 2 tenants in the group

    def test_update_tenant_group_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        data = ['1234567890abcdef', 'abcdef1234567890', '3333333333']
        request = self.factory.put('/registry/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups['1']), 3)  # 2 tenants in the group
        self.assertTrue('1234567890abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef1234567890' in tenants_groups['1'])
        self.assertTrue('3333333333' in tenants_groups['1'])

    def test_update_tenant_group_with_non_existent_id(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '2'
        data = ['1234567890abcdef', 'abcdef1234567890', '3333333333']
        request = self.factory.put('/registry/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_tenant_group_with_empty_data(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        data = []
        request = self.factory.put('/registry/gtenants/' + gtenant_id, data, format='json')
        response = tenants_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_individual_tenant_from_group_ok(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        gtenant_id = '1'
        tenant_id = '1234567890abcdef'
        request = self.factory.delete('/registry/gtenants/' + gtenant_id + '/tenants/' + tenant_id)
        response = gtenants_tenant_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check delete was successful
        request = self.factory.get('/registry/gtenants')
        response = add_tenants_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)
        self.assertEqual(len(tenants_groups['1']), 1)
        self.assertFalse('1234567890abcdef' in tenants_groups['1'])
        self.assertTrue('abcdef1234567890' in tenants_groups['1'])

    #
    # Parse tests
    #

    # To test dsl_parser correctly, we need to have metrics and filters in Redis.

    def test_parse_target_tenant_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:123456789abcdef DO SET compression')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(action_list), 1)
        target = targets[0]
        self.assertEqual(target.type, 'TENANT')
        self.assertEqual(target[1], '123456789abcdef')
        action_info = action_list[0]
        self.assertEqual(action_info.action, 'SET')
        self.assertEqual(action_info.filter, 'compression')
        self.assertEqual(action_info.execution_server, '')
        self.assertEqual(action_info.params, '')

    def test_parse_target_container_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR CONTAINER:123456789abcdef/container1 DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'CONTAINER')
        self.assertEqual(target[1], '123456789abcdef/container1')

    def test_parse_target_object_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR OBJECT:123456789abcdef/container1/object.txt DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'OBJECT')
        self.assertEqual(target[1], '123456789abcdef/container1/object.txt')

    def test_parse_target_tenant_2_actions_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:123456789abcdef DO SET compression, SET encryption')
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

    def test_parse_target_tenant_to_object_type_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:123456789abcdef DO SET compression TO OBJECT_TYPE=DOCS')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        object_list = rule_parsed.object_list
        self.assertIsNotNone(object_list)
        object_type = object_list.object_type
        self.assertIsNotNone(object_type)
        self.assertIsNotNone(object_type.object_value)
        self.assertEqual(object_type.object_value, 'DOCS')

    def test_parse_target_tenant_with_parameters_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR TENANT:123456789abcdef DO SET compression WITH cparam1=11, cparam2=12, cparam3=13')
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

    def test_parse_group_ok(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR G:1 DO SET compression')
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        action_list = rule_parsed.action_list
        self.assertEqual(len(targets), 2)
        self.assertEqual(len(action_list), 1)
        self.assertEqual(targets[0], '1234567890abcdef')
        self.assertEqual(targets[1], 'abcdef1234567890')

    def test_parse_rule_not_starting_with_for(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('TENANT:1234 DO SET compression')

    def test_parse_rule_with_invalid_target(self, mock_is_valid_request):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('FOR xxxxxxx DO SET compression')

    # TODO Add tests with wrong number of parameters, non existent parameters, wrong type parameters, ...
    # TODO Add tests for conditional rules

    #
    # load_metrics() / load_policies()
    #

    @mock.patch('registry.views.start_metric')
    def test_load_metrics(self, mock_start_metric, mock_is_valid_request):
        load_metrics()
        mock_start_metric.assert_called_with(1,'m1')

    @mock.patch('registry.views.host')
    def test_load_policies_not_alive(self, mock_host, mock_is_valid_request):
        self.r.hmset('policy:20',
                     {'alive': 'False', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression'})
        load_policies()
        self.assertEqual(len(mock_host.method_calls), 0)

    @mock.patch('registry.views.host')
    def test_load_policies_alive(self, mock_host, mock_is_valid_request):
        self.setup_dsl_parser_data()
        self.r.hmset('policy:21',
                     {'alive': 'True', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression'})
        load_policies()
        self.assertTrue(mock_host.spawn_id.called)

    @mock.patch('registry.views.host')
    def test_load_policies_alive_transient(self, mock_host, mock_is_valid_request):
        self.setup_dsl_parser_data()
        self.r.hmset('policy:21',
                     {'alive': 'True', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression TRANSIENT'})
        load_policies()
        self.assertTrue(mock_host.spawn_id.called)

    #
    # static_policy_detail()
    #

    @mock.patch('registry.views.get_project_list')
    def test_registry_static_policy_detail_ok(self, mock_get_project_list, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/registry/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["target_name"], 'tenantA')

    @mock.patch('registry.views.get_project_list')
    def test_registry_static_policy_update(self, mock_get_project_list, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a PUT request.
        data = {"execution_server": "object", "execution_server_reverse": "object"}
        request = self.factory.put('/registry/static_policy/0123456789abcdef:1', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create an instance of a GET request.
        request = self.factory.get('/registry/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["execution_server"], 'object')
        self.assertEqual(json_data["execution_server_reverse"], 'object')

    @mock.patch('registry.views.get_project_list')
    def test_registry_static_policy_detail_delete(self, mock_get_project_list, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a DELETE request.
        request = self.factory.delete('/registry/static_policy/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check there is no policy
        request = self.factory.get('/registry/static_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)

    #
    # dynamic_policy_detail()
    #

    def test_registry_dynamic_policy_detail_with_method_not_allowed(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        request = self.factory.get('/registry/dynamic_policy/123')
        response = dynamic_policy_detail(request, '123')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)





    #
    # Aux methods
    #

    @mock.patch('filters.views.is_valid_request')
    def create_storlet(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        filter_data = {'filter_type': 'storlet', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_pre_put': 'False', 'is_post_get': 'False',
                       'is_post_put': 'False', 'is_pre_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def upload_filter(self):
        # Upload a filter for the storlet 1
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            StorletData.as_view()(request, 1)

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('filters.views.is_valid_request')
    @mock.patch('registry.views.get_project_list')
    @mock.patch('filters.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def deploy_storlet(self, mock_put_object, mock_get_project_list, mock_is_valid_request):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}
        mock_is_valid_request.return_value = 'fake_token'
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
        # request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = filter_deploy(request, "1", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch('registry.views.is_valid_request')
    def create_object_type_docs(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        object_type_data = {'name': 'DOCS', 'types_list': ['txt', 'doc', 'docx']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def setup_dsl_parser_data(self):
        self.r.hmset('dsl_filter:compression', {'identifier': '1', 'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}',
                                                'activation_url': 'http://10.30.1.6:9000/filters'})
        self.r.hmset('dsl_filter:encryption', {'identifier': '2', 'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}',
                                               'activation_url': 'http://10.30.1.6:9000/filters'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
        self.r.rpush('G:1', '1234567890abcdef')
        self.r.rpush('G:2', 'abcdef1234567890')

    @mock.patch('registry.views.is_valid_request')
    def create_tenant_group_1(self, mock_is_valid_request):
        mock_is_valid_request.return_value = 'fake_token'
        tenant_group_data = ['1234567890abcdef', 'abcdef1234567890']
        request = self.factory.post('/registry/gtenants', tenant_group_data, format='json')
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
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow':'False',
                                           'in_flow': 'False', 'enabled': 'True', 'id': '1'})