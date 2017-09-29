import json

import redis
from django.conf import settings
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import storage_policies, locality_list, sort_list, sort_detail, node_list, node_detail


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class SwiftTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.api_factory = APIRequestFactory()
        self.simple_factory = RequestFactory()
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        # initializations
        self.create_storage_policies()
        self.create_proxy_sorting()
        self.create_nodes()

    def tearDown(self):
        self.r.flushdb()

    # def test_tenants_list_with_method_not_allowed(self):
    #     """ Test that DELETE requests to tenants_list() return METHOD_NOT_ALLOWED """
    #
    #     request = self.api_factory.delete('/swift/tenants')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
    #     response = tenants_list(request)
    #     self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_storage_policies_with_method_not_allowed(self):
        """ Test that PUT requests to storage_policies() return METHOD_NOT_ALLOWED """

        request = self.api_factory.put('/swift/storage_policies')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_locality_list_with_method_not_allowed(self):
        """ Test that POST requests to locality_list() return METHOD_NOT_ALLOWED """

        request = self.api_factory.post('/swift/locality/123456789abcdef/container1/object1.txt')
        response = locality_list(request, '123456789abcdef', 'container1', 'object1.txt')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_sort_list_with_method_not_allowed(self):
        """ Test that DELETE requests to sort_list() return METHOD_NOT_ALLOWED """

        request = self.api_factory.delete('/swift/sort_nodes')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_sort_detail_with_method_not_allowed(self):
        """ Test that POST requests to sort_list() return METHOD_NOT_ALLOWED """

        request = self.api_factory.post('/swift/sort_nodes/5')
        response = sort_detail(request, 5)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_all_proxy_sortings_ok(self):
        request = self.api_factory.get('/swift/sort_nodes')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        proxy_sortings = json.loads(response.content)
        self.assertEqual(len(proxy_sortings), 1)
        self.assertEqual(proxy_sortings[0]['name'], 'FakeProxySorting')

    def test_create_proxy_sorting_ok(self):
        # Create a second proxy sorting

        proxy_sorting_data = {'name': 'SecondProxySorting', 'criterion': 'second_criterion'}
        request = self.api_factory.post('/swift/sort_nodes', proxy_sorting_data, format='json')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Retrieve the list and check there are 2 elements
        request = self.api_factory.get('/swift/sort_nodes')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proxy_sortings = json.loads(response.content)
        self.assertEqual(len(proxy_sortings), 2)

    def test_create_proxy_sorting_with_empty_dict(self):
        # Create an empty proxy sorting

        request = self.api_factory.post('/swift/sort_nodes', {}, format='json')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_proxy_sorting_with_empty_data(self):
        # Create an empty proxy sorting

        request = self.api_factory.post('/swift/sort_nodes', '', format='json')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_proxy_sorting_with_unparseable_data(self):
        # Create an empty proxy sorting

        unparseable_data = '{{{{[[[[.....'
        request = self.simple_factory.post('/swift/sort_nodes', unparseable_data, 'application/json')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # TODO Add the following tests
    # def test_create_proxy_sorting_with_not_allowed_parameters(self):
    # def test_create_proxy_sorting_without_a_required_parameter(self):

    def test_get_proxy_sorting_ok(self):
        request = self.api_factory.get('/swift/sort_nodes/1')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proxy_sorting = json.loads(response.content)
        self.assertEqual(proxy_sorting['name'], 'FakeProxySorting')
        self.assertEqual(proxy_sorting['criterion'], 'fake_criterion')

    def test_update_proxy_sorting_ok(self):
        proxy_sorting_data = {'name': 'FakeProxySortingChanged', 'criterion': 'criterion changed'}
        request = self.api_factory.put('/swift/sort_nodes/1', proxy_sorting_data, format='json')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check it has been updated
        request = self.api_factory.get('/swift/sort_nodes/1')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proxy_sorting = json.loads(response.content)
        self.assertEqual(proxy_sorting['name'], 'FakeProxySortingChanged')
        self.assertEqual(proxy_sorting['criterion'], 'criterion changed')

    def test_update_proxy_sorting_with_empty_data(self):
        request = self.api_factory.put('/swift/sort_nodes/1', {}, format='json')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_proxy_sorting_with_unparseable_data(self):
        unparseable_data = '{{{{[[[[.....'

        request = self.simple_factory.put('/swift/sort_nodes/1', unparseable_data, 'application/json')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_proxy_sorting_ok(self):
        request = self.api_factory.delete('/swift/sort_nodes/1')
        response = sort_detail(request, 1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Retrieve the list and check there are 0 elements
        request = self.api_factory.get('/swift/sort_nodes')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, '[]')

    def test_storage_policy_list_ok(self):
        """ Test that GET requests to storage_policy_list() return METHOD_NOT_ALLOWED """

        request = self.api_factory.get('/swift/storage_policies')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_policies_json = json.loads(response.content)
        self.assertEqual(len(storage_policies_json), 5)

    #
    # Nodes
    #

    def test_node_list_with_method_not_allowed(self):
        request = self.api_factory.delete('/swift/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_nodes_ok(self):
        request = self.api_factory.get('/swift/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        nodes = json.loads(response.content)
        self.assertEqual(len(nodes), 3)
        node_names = [node['name'] for node in nodes]
        self.assertTrue('controller' in node_names)
        self.assertTrue('storagenode1' in node_names)
        self.assertTrue('storagenode2' in node_names)
        a_device = nodes[0]['devices'].keys()[0]
        self.assertIsNotNone(nodes[0]['devices'][a_device]['free'])

    def test_node_detail_with_method_not_allowed(self):
        server_type = 'object'
        node_id = 'storagenode1'
        # POST is not supported
        request = self.api_factory.post('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_node_detail_ok(self):
        server_type = 'object'
        node_id = 'storagenode1'
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        node = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(node['name'], 'storagenode1')

    def test_get_node_detail_with_non_existent_server_name(self):
        server_type = 'object'
        node_id = 'storagenode100000'
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_node_detail_ok(self):
        server_type = 'object'
        node_id = 'storagenode1'
        request = self.api_factory.delete('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify it was deleted
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #
    # Aux functions
    #

    def create_storage_policies(self):
        self.r.hmset("storage-policy:0", {'name': 'allnodes', 'default': 'yes', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:1", {'name': 'storage4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:2", {'name': 's0y1', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:3", {'name': 's3y4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:4", {'name': 's5y6', 'default': 'no', 'policy_type': 'replication'})

    def create_proxy_sorting(self):
        proxy_sorting_data = {'name': 'FakeProxySorting', 'criterion': 'fake_criterion'}
        request = self.api_factory.post('/swift/sort_nodes', proxy_sorting_data, format='json')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_nodes(self):
        self.r.hmset('proxy_node:controller',
                     {'ip': '192.168.2.1', 'last_ping': '1467623304.332646', 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('object_node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('object_node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
