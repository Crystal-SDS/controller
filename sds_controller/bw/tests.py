import json
import mock
import redis

from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase, override_settings
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
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        self.create_storage_policies()
        self.create_bw_policies()

    def tearDown(self):
        self.r.flushdb()

    def test_bw_list_with_method_not_allowed(self):
        """ Test that DELETE requests to bw_list() return METHOD_NOT_ALLOWED """
        request = self.factory.delete('/bw/slas')
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_bw_detail_with_method_not_allowed(self):
        """ Test that POST requests to bw_detail() return METHOD_NOT_ALLOWED """
        project_policy_key = '123456789abcdef:1'
        request = self.factory.post('/bw/sla/' + project_policy_key)
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_slas_without_auth_token(self):
        # Create an instance of a GET request without auth token
        request = self.factory.get('/bw/slas')
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_sla_detail_without_auth_token(self):
        # Create an instance of a GET request without auth token
        project_policy_key = '123456789abcdef:1'
        request = self.factory.get('/bw/sla/' + project_policy_key)
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('bw.views.requests.get')
    def test_bw_list_ok(self, mock_requests_get):
        """ Test that a GET request to bw_list() returns OK """

        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
                                               {'name': 'tenantB', 'id': 'abcdef0123456789'}]})
        mock_requests_get.return_value = resp

        request = self.factory.get('/bw/slas')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 2)
        sorted_data = sorted(json_data, key=lambda datum: datum['policy_id'])
        self.assertEqual(sorted_data[0]['policy_id'], '2')
        self.assertEqual(sorted_data[0]['project_id'], '0123456789abcdef')
        self.assertEqual(sorted_data[0]['bandwidth'], '2000')
        self.assertEqual(sorted_data[0]['project_name'], 'tenantA')
        self.assertEqual(sorted_data[0]['policy_name'], 's0y1')
        self.assertEqual(sorted_data[1]['policy_id'], '3')
        self.assertEqual(sorted_data[1]['project_id'], 'abcdef0123456789')
        self.assertEqual(sorted_data[1]['bandwidth'], '3000')
        self.assertEqual(sorted_data[1]['project_name'], 'tenantB')
        self.assertEqual(sorted_data[1]['policy_name'], 's3y4')

    @mock.patch('bw.views.requests.get')
    def test_create_sla_ok(self, mock_requests_get):
        """ Test that a POST request to bw_list() returns OK """
        sla_data = {'project_id': '0123456789abcdef', 'policy_id': '4', 'bandwidth': '4000'}
        request = self.factory.post('/bw/slas', sla_data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the SLA was created
        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
                                               {'name': 'tenantB', 'id': 'abcdef0123456789'}]})
        mock_requests_get.return_value = resp

        request = self.factory.get('/bw/slas')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 3)  # 2 --> 3
        sorted_data = sorted(json_data, key=lambda datum: datum['policy_id'])
        self.assertEqual(sorted_data[2]['policy_id'], '4')
        self.assertEqual(sorted_data[2]['project_id'], '0123456789abcdef')
        self.assertEqual(sorted_data[2]['bandwidth'], '4000')

    @mock.patch('bw.views.requests.get')
    def test_bw_detail_ok(self, mock_requests_get):
        """ Test that a GET request to bw_list() returns OK """

        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
                                               {'name': 'tenantB', 'id': 'abcdef0123456789'}]})
        mock_requests_get.return_value = resp

        project_policy_key = '0123456789abcdef:2'
        request = self.factory.get('/bw/slas/' + project_policy_key)
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['policy_id'], '2')
        self.assertEqual(json_data['project_id'], '0123456789abcdef')
        self.assertEqual(json_data['bandwidth'], '2000')
        self.assertEqual(json_data['project_name'], 'tenantA')

    @mock.patch('bw.views.requests.get')
    def test_update_sla_ok(self, mock_requests_get):
        """ Test that a PUT request to bw_detail() returns OK """
        project_policy_key = '0123456789abcdef:2'
        sla_data = {'bandwidth': '10000'}
        request = self.factory.put('/bw/slas/' + project_policy_key, sla_data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the SLA was updated
        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
                                               {'name': 'tenantB', 'id': 'abcdef0123456789'}]})
        mock_requests_get.return_value = resp
        request = self.factory.get('/bw/slas/' + project_policy_key)
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['bandwidth'], '10000')

    @mock.patch('bw.views.requests.get')
    def test_delete_sla_ok(self, mock_requests_get):
        """ Test that a DELETE request to bw_detail() returns OK """
        project_policy_key = '0123456789abcdef:2'
        request = self.factory.delete('/bw/slas/' + project_policy_key)
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_detail(request, project_policy_key)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the SLA was deleted
        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
                                               {'name': 'tenantB', 'id': 'abcdef0123456789'}]})
        mock_requests_get.return_value = resp

        request = self.factory.get('/bw/slas')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = bw_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 1)  # 2 --> 1
        self.assertEqual(json_data[0]['policy_id'], '3')

    #
    # Aux functions
    #

    def create_storage_policies(self):
        self.r.hmset("storage-policy:0", {'name': 'allnodes', 'default': 'yes', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:1", {'name': 'storage4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:2", {'name': 's0y1', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:3", {'name': 's3y4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:4", {'name': 's5y6', 'default': 'no', 'policy_type': 'replication'})

    def create_bw_policies(self):
        self.r.hmset('bw:AUTH_0123456789abcdef', {'2': '2000'})
        self.r.hmset('bw:AUTH_abcdef0123456789', {'3': '3000'})