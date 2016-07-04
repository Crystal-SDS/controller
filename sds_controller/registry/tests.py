import json

import redis
import mock

from django.test import TestCase, override_settings
from django.conf import settings
from django.http import HttpResponse
from pyparsing import ParseException
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import policy_list
from storlet.views import storlet_list, storlet_deploy, StorletData
from .views import object_type_list, object_type_detail
from .dsl_parser import parse


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
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


    def tearDown(self):
        self.r.flushdb()

    #
    # Static policy tests
    #

    @mock.patch('registry.views.requests.get')
    def test_registry_static_policy(self, mock_requests_get):
        resp = HttpResponse()
        resp.content = json.dumps({'tenants': [{'name': 'tenantA', 'id': '0123456789abcdef'},
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
    # object_type tests
    #

    def test_object_type_list_with_method_not_allowed(self):
        request = self.factory.delete('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_object_type_detail_with_method_not_allowed(self):
        name = 'AUDIO'
        object_type_data = {'name': name, 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type/' + name, object_type_data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_object_types_ok(self):
        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        object_types = json.loads(response.content)

        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 3)

    def test_create_object_type_ok(self):
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

    def test_create_object_type_without_name(self):
        # Create a second object type without name --> ERROR
        object_type_data = {'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_an_existing_name(self):
        # Create a second object type with an existing name --> ERROR
        object_type_data = {'name': 'DOCS', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_without_types_list(self):
        # Create a second object type without_types_list --> ERROR
        object_type_data = {'name': 'VIDEO'}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_empty_types_list(self):
        # Create a second object type with empty types_list --> ERROR
        object_type_data = {'name': 'VIDEO', 'types_list': []}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_object_type_detail_ok(self):
        name = 'DOCS'
        request = self.factory.get('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        object_type = json.loads(response.content)
        self.assertEqual(object_type['name'], name)
        self.assertEqual(len(object_type['types_list']), 3)
        self.assertTrue('txt' in object_type['types_list'])

    def test_object_type_detail_with_non_existent_name(self):
        name = 'AUDIO'
        request = self.factory.get('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_object_type_ok(self):
        name = 'DOCS'
        request = self.factory.delete('/registry/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/registry/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_object_type_with_non_existent_name(self):
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

    def test_update_object_type_ok(self):
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

    def test_update_object_type_ok_with_more_extensions(self):
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

    def test_update_object_type_with_non_existent_name(self):
        name = 'VIDEO'
        data = ['avi', 'mkv']
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_object_type_with_empty_list(self):
        # It's wrong to send an empty list
        name = 'DOCS'
        data = []
        request = self.factory.put('/registry/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #
    # Parse tests
    #

    # TODO To test dsl_parser correctly, we need to have metrics and filters in Redis.

    def test_parse_target_tenant_ok(self):
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

    def test_parse_target_container_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR CONTAINER:123456789abcdef/container1 DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'CONTAINER')
        self.assertEqual(target[1], '123456789abcdef/container1')

    def test_parse_target_object_ok(self):
        self.setup_dsl_parser_data()
        has_condition_list, rule_parsed = parse('FOR OBJECT:123456789abcdef/container1/object.txt DO SET compression')
        self.assertIsNotNone(rule_parsed)
        targets = rule_parsed.target
        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target.type, 'OBJECT')
        self.assertEqual(target[1], '123456789abcdef/container1/object.txt')

    def test_parse_target_tenant_2_actions_ok(self):
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

    def test_parse_target_tenant_to_object_type_ok(self):
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

    def test_parse_rule_not_starting_with_for(self):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('TENANT:1234 DO SET compression')

    def test_parse_rule_with_invalid_target(self):
        self.setup_dsl_parser_data()
        with self.assertRaises(ParseException):
            parse('FOR xxxxxxx DO SET compression')


    # TODO tests for conditional rules


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

    def create_object_type_docs(self):
        object_type_data = {'name': 'DOCS', 'types_list': ['txt', 'doc', 'docx']}
        request = self.factory.post('/registry/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def setup_dsl_parser_data(self):
        self.r.hmset('filter:compression', {'valid_parameters': '["cparam1", "cparam2", "cparam3"]'})
        self.r.hmset('filter:encryption', {'valid_parameters': '["eparam1", "eparam2", "eparam3"]'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
