import redis

from django.test import TestCase, override_settings
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
        self.factory = APIRequestFactory()

    def tearDown(self):
        r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        r.flushdb()

    def test_tenants_list_with_method_not_allowed(self):
        """ Test that DELETE requests to tenants_list() return METHOD_NOT_ALLOWED """
        request = self.factory.delete('/swift/tenants')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_storage_policies_with_method_not_allowed(self):
        """ Test that GET requests to storage_policies() return METHOD_NOT_ALLOWED """
        request = self.factory.get('/swift/spolicies')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_locality_list_with_method_not_allowed(self):
        """ Test that POST requests to locality_list() return METHOD_NOT_ALLOWED """
        request = self.factory.post('/swift/locality/123456789abcdef/container1/object1.txt')
        response = locality_list(request, '123456789abcdef', 'container1', 'object1.txt')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_sort_list_with_method_not_allowed(self):
        """ Test that DELETE requests to sort_list() return METHOD_NOT_ALLOWED """
        request = self.factory.delete('/swift/sort_nodes')
        response = sort_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_sort_detail_with_method_not_allowed(self):
        """ Test that POST requests to sort_list() return METHOD_NOT_ALLOWED """
        request = self.factory.post('/swift/sort_nodes/5')
        response = sort_detail(request, 5)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_tenants_without_auth_token(self):
        # Create an instance of a GET request without auth token
        request = self.factory.get('/swift/tenants')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_tenant_without_auth_token(self):
        # Create an instance of a POST request without auth token
        request = self.factory.post('/swift/tenants', {}, format='json')
        response = tenants_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_storage_policy_without_auth_token(self):
        # Create an instance of a POST request without auth token
        request = self.factory.post('/swift/spolicies', {}, format='json')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
