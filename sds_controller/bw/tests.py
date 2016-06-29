import redis

from django.test import TestCase, override_settings
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import bw_list, bw_detail


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

    def test_bw_list_with_method_not_allowed(self):
        """ Test that DELETE requests to bw_list() return METHOD_NOT_ALLOWED """
        request = self.factory.delete('/bw/slas')
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_bw_detail_with_method_not_allowed(self):
        """ Test that POST requests to bw_detail() return METHOD_NOT_ALLOWED """
        tenant_key = '123456789abcdef:1'
        request = self.factory.post('/bw/sla/' + tenant_key)
        response = bw_detail(request, tenant_key)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_slas_without_auth_token(self):
        # Create an instance of a GET request without auth token
        request = self.factory.get('/bw/slas')
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_sla_detail_without_auth_token(self):
        # Create an instance of a GET request without auth token
        tenant_key = '123456789abcdef:1'
        request = self.factory.get('/bw/sla/' + tenant_key)
        response = bw_detail(request, tenant_key)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
