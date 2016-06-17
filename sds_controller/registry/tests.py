import json

import redis
import mock

from django.test import TestCase, override_settings
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import policy_list
from storlet.views import storlet_list, storlet_deploy, StorletData

# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL = redis.ConnectionPool(host='localhost', port=6379, db=10))
class RegistryTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.factory = APIRequestFactory()
        self.create_storlet()
        self.upload_filter()
        self.deploy_storlet()


    def tearDown(self):
        r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        r.flushdb()

    @mock.patch('registry.views.requests.get')
    def test_registry_static_policy(self, mock_requests_get):
        resp = HttpResponse()
        resp.content = json.dumps({'tenants':[{'name': 'tenantA', 'id': '0123456789abcdef'},
                                              {'name': 'tenantB', 'id': '2'}]})
        mock_requests_get.return_value = resp

        # Create an instance of a GET request.
        request = self.factory.get('/registry/static_policy')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data[0]["target_name"], 'tenantA')

    def test_registry_static_policy_without_auth_token(self):
        # Create an instance of a GET request without auth token
        request = self.factory.get('/registry/static_policy')
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'name': 'FakeFilter', 'language': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def upload_filter(self):
        # Upload a filter for the storlet 1
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            StorletData.as_view()(request, 1)

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('storlet.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def deploy_storlet(self, mock_put_object):
        # Call storlet_deploy
        policy_data = {
            "policy_id": "1",
            "object_type": None,
            "object_size": None,
            "execution_order": "1",
            "params": ""
        }
        request = self.factory.put('/0123456789abcdef/deploy/1', policy_data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = storlet_deploy(request, "1", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)