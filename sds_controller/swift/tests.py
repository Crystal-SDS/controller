import json
import redis

from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import tenants_list, storage_policies, locality_list, sort_list, sort_detail


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class BwTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.api_factory = APIRequestFactory()
        self.simple_factory = RequestFactory()
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        # initializations
        self.create_storage_policies()
        self.create_proxy_sorting()

    def tearDown(self):
        self.r.flushdb()

    def test_tenants_list_with_method_not_allowed(self):
        """ Test that DELETE requests to tenants_list() return METHOD_NOT_ALLOWED """
        request = self.api_factory.delete('/swift/tenants')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_storage_policies_with_method_not_allowed(self):
        """ Test that GET requests to storage_policies() return METHOD_NOT_ALLOWED """
        request = self.api_factory.get('/swift/spolicies')
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

    def test_get_tenants_without_auth_token(self):
        # Create an instance of a GET request without auth token
        request = self.api_factory.get('/swift/tenants')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_tenant_without_auth_token(self):
        # Create an instance of a POST request without auth token
        request = self.api_factory.post('/swift/tenants', {}, format='json')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_storage_policy_without_auth_token(self):
        # Create an instance of a POST request without auth token
        request = self.api_factory.post('/swift/spolicies', {}, format='json')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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