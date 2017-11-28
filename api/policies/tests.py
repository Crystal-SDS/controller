import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from pyparsing import ParseException
from rest_framework import status
from rest_framework.test import APIRequestFactory
from policies.dsl_parser import parse, parse_condition
from filters.views import filter_list, filter_deploy, FilterData
from policies.views import object_type_list, object_type_detail, static_policy_detail, dynamic_policy_detail, policy_list, \
    access_control, access_control_detail
from projects.views import add_projects_group


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class PoliciesTestCase(TestCase):
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
        self.create_acls()

    def tearDown(self):
        self.r.flushdb()

    #
    # Static/dynamic policy tests
    #

    @mock.patch('policies.views.get_project_list')
    def test_registry_static_policy(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/policies/static')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data[0]["target_name"], 'tenantA')

    def test_registry_dynamic_policy(self):
        # Create an instance of a GET request.
        request = self.factory.get('/policies/dynamic')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)  # is empty

    @mock.patch('policies.views.deploy_static_policy')
    def test_registry_static_policy_create_ok(self, mock_deploy_static_policy):
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef DO SET compression"
        request = self.factory.post('/policies/static', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_deploy_static_policy.called)

    @mock.patch('policies.views.get_project_list')
    @mock.patch('policies.views.set_filter')
    def test_registry_static_policy_create_set_filter_ok(self, mock_set_filter, mock_get_project_list):
        self.setup_dsl_parser_data()

        self.r.lpush('projects_crystal_enabled', '0123456789abcdef')
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef DO SET compression WITH bw=2 ON PROXY TO OBJECT_TYPE=DOCS"
        request = self.factory.post('/policies/static', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_set_filter.called)
        expected_policy_data = {'object_size': '', 'execution_order': 2, 'object_type': 'DOCS', 'params': mock.ANY,
                                'execution_server': 'PROXY', 'callable': False, 'object_tag': '', 'policy_id': 2,
                                'object_name': 'txt, doc, docx'}
        mock_set_filter.assert_called_with(mock.ANY, '0123456789abcdef', mock.ANY, expected_policy_data, 'fake_token')

    @mock.patch('policies.views.deploy_dynamic_policy')
    def test_registry_dynamic_policy_create_ok(self, mock_deploy_dynamic_policy):
        self.setup_dsl_parser_data()

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/policies/static', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_deploy_dynamic_policy.called)

    @mock.patch('policies.views.get_project_list')
    @mock.patch('policies.views.create_local_host')
    def test_registry_dynamic_policy_create_spawn_ok(self, mock_create_local_host, mock_get_project_list):
        self.setup_dsl_parser_data()

        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}
        self.r.lpush('projects_crystal_enabled', '0123456789abcdef')

        # Create an instance of a POST request.
        data = "FOR TENANT:0123456789abcdef WHEN metric1 > 5 DO SET compression"
        request = self.factory.post('/policies/dynamic', data, content_type='text/plain')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        request.META['HTTP_HOST'] = 'fake_host'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_create_local_host.called)
        self.assertTrue(mock_create_local_host.return_value.spawn.called)
        self.assertTrue(self.r.exists('policy:2'))
        policy_data = self.r.hgetall('policy:2')
        self.assertEqual(policy_data['target_id'], '0123456789abcdef')
        self.assertEqual(policy_data['filter'], 'compression')
        self.assertEqual(policy_data['condition'], 'metric1 > 5')

    #
    # static_policy_detail()
    #

    @mock.patch('policies.views.get_project_list')
    def test_registry_static_policy_detail_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a GET request.
        request = self.factory.get('/policies/static/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["target_name"], 'tenantA')

    @mock.patch('policies.views.get_project_list')
    def test_registry_static_policy_update(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a PUT request.
        data = {"execution_server": "object", "reverse": "object"}
        request = self.factory.put('/policies/static/0123456789abcdef:1', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create an instance of a GET request.
        request = self.factory.get('/policies/static/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data["execution_server"], 'object')
        self.assertEqual(json_data["reverse"], 'object')

    @mock.patch('policies.views.get_project_list')
    def test_registry_static_policy_detail_delete(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # Create an instance of a DELETE request.
        request = self.factory.delete('/policies/static/0123456789abcdef:1')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = static_policy_detail(request, '0123456789abcdef:1')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check there is no policy
        request = self.factory.get('/policies/static')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = policy_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 0)

    #
    # dynamic_policy_detail()
    #

    def test_registry_dynamic_policy_detail_with_method_not_allowed(self):
        request = self.factory.get('/policies/dynamic/123')
        request.META['HTTP_HOST'] = 'fake_host'
        response = dynamic_policy_detail(request, '123')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

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

    def test_parse_target_tenant_to_object_type_tag_size_ok(self):
        self.setup_dsl_parser_data()
        rule_str = 'FOR TENANT:0123456789abcdef DO SET compression TO OBJECT_TAG=tagtag, OBJECT_SIZE>10, OBJECT_TYPE=DOCS'
        has_condition_list, rule_parsed = parse(rule_str)
        self.assertFalse(has_condition_list)
        self.assertIsNotNone(rule_parsed)
        object_list = rule_parsed.object_list
        self.assertIsNotNone(object_list)
        object_type = object_list.object_type
        self.assertIsNotNone(object_type)
        self.assertIsNotNone(object_type.object_value)
        self.assertEqual(object_type.object_value, 'DOCS')
        object_tag = object_list.object_tag
        self.assertIsNotNone(object_tag)
        self.assertIsNotNone(object_tag.object_value)
        self.assertEqual(object_tag.object_value, 'tagtag')
        object_size = object_list.object_size
        self.assertIsNotNone(object_size)
        self.assertIsNotNone(object_size.object_value)
        self.assertEqual(object_size.object_value, '10')
        self.assertEqual(object_size.operand, '>')

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

    def test_parse_condition_ok(self):
        self.setup_dsl_parser_data()
        condition_list = parse_condition("metric1 > 5.0 OR metric1 < 2.0")
        self.assertIsNotNone(condition_list)
        self.assertEqual(condition_list, [['metric1', '>', '5.0'], 'OR', ['metric1', '<', '2.0']])

    #
    # object_type tests
    #

    def test_object_type_list_with_method_not_allowed(self):
        request = self.factory.delete('/policies/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_object_type_detail_with_method_not_allowed(self):
        name = 'AUDIO'
        object_type_data = {'name': name, 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/policies/object_type/' + name, object_type_data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_object_types_ok(self):
        request = self.factory.get('/policies/object_type')
        response = object_type_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        object_types = json.loads(response.content)

        self.assertEqual(object_types[0]['name'], "DOCS")
        self.assertEqual(len(object_types[0]['types_list']), 3)

    def test_create_object_type_ok(self):
        # Create a second object type:
        object_type_data = {'name': 'VIDEO', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/policies/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # obtain the list
        request = self.factory.get('/policies/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(len(object_types), 2)

    def test_create_object_type_without_name(self):
        # Create a second object type without name --> ERROR
        object_type_data = {'types_list': ['avi', 'mkv']}
        request = self.factory.post('/policies/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_an_existing_name(self):
        # Create a second object type with an existing name --> ERROR
        object_type_data = {'name': 'DOCS', 'types_list': ['avi', 'mkv']}
        request = self.factory.post('/policies/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_without_types_list(self):
        # Create a second object type without_types_list --> ERROR
        object_type_data = {'name': 'VIDEO'}
        request = self.factory.post('/policies/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_object_type_with_empty_types_list(self):
        # Create a second object type with empty types_list --> ERROR
        object_type_data = {'name': 'VIDEO', 'types_list': []}
        request = self.factory.post('/policies/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_object_type_detail_ok(self):
        name = 'DOCS'
        request = self.factory.get('/policies/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        object_type = json.loads(response.content)
        self.assertEqual(object_type['name'], name)
        self.assertEqual(len(object_type['types_list']), 3)
        self.assertTrue('txt' in object_type['types_list'])

    def test_object_type_detail_with_non_existent_name(self):
        name = 'AUDIO'
        request = self.factory.get('/policies/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_object_type_ok(self):
        name = 'DOCS'
        request = self.factory.delete('/policies/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/policies/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_object_type_with_non_existent_name(self):
        name = 'AUDIO'
        request = self.factory.delete('/policies/object_type/' + name)
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/policies/object_type')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        object_types = json.loads(response.content)
        self.assertEqual(object_types[0]['name'], "DOCS")

    def test_update_object_type_ok(self):
        name = 'DOCS'
        data = ['txt', 'doc']
        request = self.factory.put('/policies/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/policies/object_type')
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
        request = self.factory.put('/policies/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/policies/object_type')
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
        request = self.factory.put('/policies/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_object_type_with_empty_list(self):
        # It's wrong to send an empty list
        name = 'DOCS'
        data = []
        request = self.factory.put('/policies/object_type/' + name, data, format='json')
        response = object_type_detail(request, name)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #
    # ACL's
    #

    @mock.patch('policies.views.get_project_list')
    def test_access_control_get_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}

        request = self.factory.get('/policies/acl/')
        response = access_control(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acls = json.loads(response.content)
        self.assertEqual(len(acls), 1)
        acl = acls[0]
        self.assertEqual(acl['user_id'], 'a1a1a1a1a1a1')
        self.assertEqual(acl['target_name'], 'tenantA/container1')
        self.assertEqual(acl['target_id'], '0123456789abcdef:container1')
        self.assertEqual(acl['write'], True)
        self.assertEqual(acl['read'], True)
        self.assertEqual(acl['id'], '1')

    @mock.patch('policies.views.get_project_list')
    def test_access_control_post_list_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}

        acl_data = {'project_id': '0123456789abcdef', 'container_id': 'container2', 'identity': 'user_id:a1a1a1a1a1a1', 'access': 'list'}
        request = self.factory.post('/policies/acl/', acl_data, format='json')
        response = access_control(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check it has been created
        request = self.factory.get('/policies/acl/')
        response = access_control(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acls = json.loads(response.content)
        self.assertEqual(len(acls), 2)

    @mock.patch('policies.views.get_project_list')
    def test_access_control_post_read_group_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}

        acl_data = {'project_id': '0123456789abcdef', 'container_id': 'container2', 'identity': 'group_id:g2g2g2', 'access': 'read'}
        request = self.factory.post('/policies/acl/', acl_data, format='json')
        response = access_control(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check it has been created
        policy_id = '0123456789abcdef:container2:2'
        request = self.factory.get('/policies/acl/' + policy_id)
        response = access_control_detail(request, policy_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acl_policy = json.loads(response.content)
        self.assertEqual(acl_policy['target_name'], 'tenantA/container2')
        self.assertFalse(acl_policy['list'])
        self.assertFalse(acl_policy['write'])
        self.assertTrue(acl_policy['read'])
        self.assertEqual(acl_policy['group_id'], 'g2g2g2')

    @mock.patch('policies.views.get_project_list')
    def test_access_control_delete_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}

        policy_id = '0123456789abcdef:container1:1'
        request = self.factory.delete('/policies/acl/' + policy_id)
        response = access_control_detail(request, policy_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check it has been deleted
        request = self.factory.get('/policies/acl/')
        response = access_control(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acls = json.loads(response.content)
        self.assertEqual(len(acls), 0)

    @mock.patch('policies.views.get_project_list')
    def test_access_control_update_ok(self, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}

        policy_id = '0123456789abcdef:container1:1'
        acl_data = {'access': 'list'}
        request = self.factory.put('/policies/acl/' + policy_id, acl_data, format='json')
        response = access_control_detail(request, policy_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check it has been updated
        request = self.factory.get('/policies/acl/' + policy_id)
        response = access_control_detail(request, policy_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        acl_policy = json.loads(response.content)
        self.assertTrue(acl_policy['list'])
        self.assertFalse(acl_policy['write'])
        self.assertFalse(acl_policy['read'])

    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'filter_type': 'storlet', 'language': 'java', 'dsl_name': 'fake', 'interface_version': '1.0',
                       'dependencies': '', 'main': 'com.example.FakeMain', 'put': 'False', 'get': 'False',
                       'valid_parameters': '', 'execution_server': 'proxy', 'reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def upload_filter(self):
        # Upload a filter for the filter "fake"
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/fake/data', {'file': fp})
            FilterData.as_view()(request, 'fake')

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('policies.views.get_project_list')
    @mock.patch('filters.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def deploy_storlet(self, mock_put_object, mock_get_project_list):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', '2': 'tenantB'}

        # mock_requests_get.return_value = self.keystone_get_tenants_response()
        # mock_get_crystal_token.return_value = settings.SWIFT_URL + settings.SWIFT_API_VERSION + '/AUTH_0123456789abcdef', 'fake_token'

        # Call filter_deploy
        policy_data = {
            "policy_id": "1",
            "object_type": '',
            "object_size": None,
            "object_tag": None,
            "object_name": None,
            "execution_order": "1",
            "params": ""
        }
        request = self.factory.put('/0123456789abcdef/deploy/fake', policy_data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = filter_deploy(request, "fake", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_object_type_docs(self):
        object_type_data = {'name': 'DOCS', 'types_list': ['txt', 'doc', 'docx']}
        request = self.factory.post('/controller/object_type', object_type_data, format='json')
        response = object_type_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def setup_dsl_parser_data(self):
        # Simplified filter data:
        self.r.hmset('filter:compression', {'valid_parameters': '{"cparam1": "integer", "cparam2": "integer", "cparam3": "integer"}'})
        self.r.hmset('filter:encryption', {'valid_parameters': '{"eparam1": "integer", "eparam2": "bool", "eparam3": "string"}'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})

    def create_tenant_group_1(self):
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789'])}
        request = self.factory.post('/projects/groups', tenant_group_data, format='json')
        response = add_projects_group(request)
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
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'status': 'Running', 'get': 'False', 'put': 'False',
                                           'execution_server': 'object', 'replicate': 'True', 'ssync': 'True', 'id': '1'})

    def create_global_controllers(self):
        self.r.incr("controllers:id")  # setting autoincrement to 1
        self.r.hmset('controller:1', {'class_name': 'MinTenantSLOGlobalSpareBWShare',
                                      'controller_name': 'min_slo_tenant_global_share_spare_bw_v2.py',
                                      'valid_parameters': 'method={put|get}', 'id': '1', 'instances': 0,
                                      'enabled': 'False', 'description': 'Fake description'})

    def create_acls(self):
        self.r.incr('acls:id')
        acl_data = {'user_id': 'a1a1a1a1a1a1', 'read': True, 'object_type': '', 'write': True, 'object_tag': ''}
        self.r.hmset('acl:0123456789abcdef:container1', {'1': json.dumps(acl_data)})
