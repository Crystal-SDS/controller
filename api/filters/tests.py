import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import dependency_list, dependency_detail, filter_list, filter_detail, filter_deploy, unset_filter, FilterData
from policies.views import slo_list, slo_detail


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"))
class FiltersTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.factory = APIRequestFactory()
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.create_storlet()
        self.create_dependency()
        self.create_storage_policies()
        self.create_sample_bw_policies()

    def tearDown(self):
        self.r.flushdb()

    def test_list_storlet_ok(self):
        """
        Retrieve storlet list
        """
        # Create an instance of a GET request.
        request = self.factory.get('/filters')
        response = filter_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        storlets = json.loads(response.content)
        self.assertEqual(storlets[0]['main'], "com.example.FakeMain")
        self.assertEqual(storlets[0]['id'], "1")

    def test_delete_storlet_ok(self):
        """
        Delete a storlet
        """
        request = self.factory.delete('/filters/fake')
        response = filter_detail(request, "fake")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/filters')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_storlet_if_not_exists(self):
        """
        Delete a non existent storlet
        """
        request = self.factory.delete('/filters/fake2')
        response = filter_detail(request, "fake2")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_storlet_ok(self):
        """
        Update a storlet
        """
        filter_updated_data = {
            'interface_version': '',
            'object_metadata': '', 'main': 'com.example.UpdatedFakeMain', 'is_pre_put': 'False', 'is_post_get': 'False',
            'is_post_put': 'False', 'is_pre_get': 'False',
            'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.put('/filters/fake', filter_updated_data, format='json')
        response = filter_detail(request, "fake")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/filters')
        response = filter_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(storlets[0]['main'], 'com.example.UpdatedFakeMain')

    def test_update_storlet_with_invalid_requests(self):
        # Wrong content type
        request = self.factory.put('/filters/fake', 'dummy test', content_type='text/plain')
        response = filter_detail(request, "fake")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_storlet_ok(self):
        """
        Create 2 storlets
        """
        # Create a second storlet
        filter_data = {'filter_type': 'storlet', 'language': 'java', 'dsl_name': 'secondfake', 'interface_version': '1.0',
                       'dependencies': '', 'main': 'com.example.SecondMain', 'put': 'False', 'get': 'False',
                       'valid_parameters': '', 'execution_server': 'proxy', 'reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = filter_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(len(storlets), 2)
        sorted_list = sorted(storlets, key=lambda st: st['id'])
        self.assertEqual(sorted_list[0]['main'], 'com.example.FakeMain')
        self.assertEqual(sorted_list[1]['main'], 'com.example.SecondMain')

    def test_create_storlets_are_sorted_by_id(self):
        """
        Create several storlets and check they are returned as a sorted list by identifier
        """
        # Create a second storlet
        filter_data = {'filter_type': 'storlet', 'language': 'java', 'dsl_name': 'secondfake', 'interface_version': '1.0',
                       'dependencies': '', 'main': 'com.example.SecondMain', 'put': 'False', 'get': 'False',
                       'valid_parameters': '', 'execution_server': 'proxy', 'reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create a third storlet
        filter_data = {'filter_type': 'storlet', 'language': 'java', 'dsl_name': 'thirdfake', 'interface_version': '1.0',
                       'dependencies': '', 'main': 'com.example.ThirdMain', 'put': 'False', 'get': 'False',
                       'valid_parameters': '', 'execution_server': 'proxy', 'reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create a Fourth storlet
        filter_data = {'filter_type': 'storlet', 'language': 'java', 'dsl_name': 'fourthfake', 'interface_version': '1.0',
                       'dependencies': '', 'main': 'com.example.FourthMain', 'put': 'False', 'get': 'False',
                       'valid_parameters': '', 'execution_server': 'proxy', 'reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = filter_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(len(storlets), 4)
        self.assertEqual(storlets[0]['main'], 'com.example.FakeMain')
        self.assertEqual(storlets[1]['main'], 'com.example.SecondMain')
        self.assertEqual(storlets[2]['main'], 'com.example.ThirdMain')
        self.assertEqual(storlets[3]['main'], 'com.example.FourthMain')

    def test_create_storlet_with_invalid_request(self):
        # Invalid param
        filter_data = {'wrongparam': 'dummy', 'filter_type': 'storlet'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Wrong content type
        request = self.factory.post('/filters/', 'dummy_text', content_type='text/plain')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # with name present
        filter_data = {'filter_name': 'secondFilter', 'filter_type': 'storlet', 'interface_version': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_pre_put': 'False', 'is_post_get': 'False',
                       'is_post_put': 'False', 'is_pre_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = filter_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_storlet_data_ok(self):
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/fake/data', {'file': fp})
            response = FilterData.as_view()(request, 'fake')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = filter_list(request)
        storlets = json.loads(response.content)
        self.assertTrue(len(storlets[0]['etag']) > 0)

    def test_upload_storlet_data_to_non_existent_storlet(self):
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/fake2/data', {'file': fp})
            response = FilterData.as_view()(request, 'fake2')
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_storlet_with_wrong_extension(self):
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/fake/data', {'file': fp})
            response = FilterData.as_view()(request, 'fake')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('filters.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def test_filter_deploy_to_project_ok(self, mock_put_object):
        # Upload a filter for the storlet 1
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/fake/data', {'file': fp})
            FilterData.as_view()(request, 'fake')

        # Call filter_deploy
        data = {"filter_id": "fake", "target_id": "0123456789abcdef",
                "execution_server": "proxy", "execution_server_reverse": "proxy",
                "object_type": "", "object_size": "", "object_tag": "", "params": ""}

        request = self.factory.put('/filters/0123456789abcdef/deploy/fake', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = filter_deploy(request, "fake", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.content, '1')
        mock_put_object.assert_called_with(settings.SWIFT_URL + "/AUTH_0123456789abcdef",
                                           'fake_token', ".storlet", "test-1.0.jar", mock.ANY, mock.ANY, mock.ANY,
                                           mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
        self.assertTrue(self.r.hexists("pipeline:0123456789abcdef", "1"))
        dumped_data = self.r.hget("pipeline:0123456789abcdef", "1")
        json_data = json.loads(dumped_data)
        self.assertEqual(json_data["filter_name"], "test-1.0.jar")

    @mock.patch('filters.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def test_filter_deploy_to_project_and_container_ok(self, mock_put_object):
        # Upload a filter for the storlet 1
        with open('test_data/test-1.0.jar', 'r') as fp:
            request = self.factory.put('/filters/fake/data', {'file': fp})
            FilterData.as_view()(request, 'fake')

        # Call filter_deploy
        data = {"filter_id": "fake", "target_id": "0123456789abcdef",
                "execution_server": "proxy", "execution_server_reverse": "proxy",
                "object_type": "", "object_size": "", "object_tag": "", "params": ""}

        request = self.factory.put('/filters/0123456789abcdef/container1/deploy/fake', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = filter_deploy(request, "fake", "0123456789abcdef", "container1")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.content, '1')
        mock_put_object.assert_called_with(settings.SWIFT_URL + "/AUTH_0123456789abcdef",
                                           'fake_token', ".storlet", "test-1.0.jar", mock.ANY, mock.ANY, mock.ANY,
                                           mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
        self.assertTrue(self.r.hexists("pipeline:0123456789abcdef:container1", "1"))
        dumped_data = self.r.hget("pipeline:0123456789abcdef:container1", "1")
        json_data = json.loads(dumped_data)
        self.assertEqual(json_data["filter_name"], "test-1.0.jar")

    def test_get_all_dependencies_ok(self):
        request = self.factory.get('/filters/dependencies')
        response = dependency_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, '[]')
        dependencies = json.loads(response.content)
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0]['name'], 'DependencyName')

    def test_create_dependency_ok(self):
        dependency_data = {'name': 'SecondDependencyName', 'version': '2.0', 'permissions': '0755'}
        request = self.factory.post('/filters/dependencies', dependency_data, format='json')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check dependency was created successfully
        request = self.factory.get('/filters/dependencies')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dependencies = json.loads(response.content)
        self.assertEqual(len(dependencies), 2)
        dependency_names = [dependency['name'] for dependency in dependencies]
        self.assertTrue('DependencyName' in dependency_names)
        self.assertTrue('SecondDependencyName' in dependency_names)

    def test_get_dependency_ok(self):
        dependency_id = 1
        request = self.factory.get('/filters/dependencies/' + str(dependency_id))
        response = dependency_detail(request, dependency_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dependency = json.loads(response.content)
        self.assertEqual(dependency['name'], 'DependencyName')

    def test_update_dependency_ok(self):
        dependency_id = 1
        dependency_data = {'name': 'DependencyName', 'version': '1.1', 'permissions': '0777'}
        request = self.factory.put('/filters/dependencies/' + str(dependency_id), dependency_data, format='json')
        response = dependency_detail(request, dependency_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check dependency was updated successfully
        request = self.factory.get('/filters/dependencies')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dependencies = json.loads(response.content)
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0]['version'], '1.1')
        self.assertEqual(dependencies[0]['permissions'], '0777')

    def test_delete_dependency_ok(self):
        dependency_id = 1
        request = self.factory.delete('/filters/dependencies/' + str(dependency_id))
        response = dependency_detail(request, dependency_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check dependency was deleted successfully
        request = self.factory.get('/filters/dependencies')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dependencies = json.loads(response.content)
        self.assertEqual(len(dependencies), 0)

    @mock.patch('filters.views.swift_client.delete_object')
    def test_unset_filter_ok(self, mock_delete_object):
        data20 = {'filter_name': 'XXXXX'}
        data21 = {'filter_name': 'test-1.0.jar'}
        self.r.hmset('pipeline:0123456789abcdef', {'20': json.dumps(data20), '21': json.dumps(data21)})
        unset_filter(self.r, '0123456789abcdef', {'filter_type': 'storlet', 'filter_name': 'test-1.0.jar'}, 'fake_token')
        mock_delete_object.assert_called_with(settings.SWIFT_URL + "/AUTH_0123456789abcdef",
                                              'fake_token', ".storlet", "test-1.0.jar", mock.ANY, mock.ANY, mock.ANY,
                                              mock.ANY, mock.ANY)
        self.assertFalse(self.r.hexists("pipeline:0123456789abcdef", "21"))  # 21 was deleted
        self.assertTrue(self.r.hexists("pipeline:0123456789abcdef", "20"))  # 20 was not deleted

    # slo_list / slo_detail

    def test_slo_list_with_method_not_allowed(self):
        """ Test that DELETE requests to slo_list() return METHOD_NOT_ALLOWED """
        request = self.factory.delete('/filters/slos')
        response = slo_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_slo_detail_with_method_not_allowed(self):
        """ Test that POST requests to slo_detail() return METHOD_NOT_ALLOWED """
        dsl_filter = 'bandwidth'
        slo_name = 'get_bw'
        target = 'AUTH_0123456789abcdef#1'
        request = self.factory.post('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target)
        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_slo_list_ok(self):
        """ Test that a GET request to slo_list() returns OK """

        request = self.factory.get('/filters/slos')
        response = slo_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 6)

        sorted_data = sorted(json_data, key=lambda datum: (datum['target'], datum['slo_name']))
        self.assertEqual(sorted_data[0]['value'], '20')
        self.assertEqual(sorted_data[1]['value'], '30')
        self.assertEqual(sorted_data[2]['value'], '50')
        self.assertEqual(sorted_data[3]['value'], '10')
        self.assertEqual(sorted_data[4]['value'], '15')
        self.assertEqual(sorted_data[5]['value'], '25')

    def test_create_slo_ok(self):
        """ Test that a POST request to slo_list() returns OK """
        slo_data = {'dsl_filter': 'bandwidth', 'slo_name': 'get_bw', 'target': 'AUTH_0123456789abcdef#4', 'value': '10'}
        request = self.factory.post('/filters/slos', slo_data, format='json')
        response = slo_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the SLO was created
        request = self.factory.get('/filters/slos')
        response = slo_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 7)  # 6 --> 7
        sorted_data = sorted(json_data, key=lambda datum: datum['target'])
        self.assertEqual(sorted_data[3]['value'], '10')
        self.assertEqual(sorted_data[3]['slo_name'], 'get_bw')
        self.assertEqual(sorted_data[3]['dsl_filter'], 'bandwidth')

    def test_slo_detail_ok(self):
        """ Test that a GET request to slo_detail() returns OK """

        # mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}
        dsl_filter = 'bandwidth'
        slo_name = 'get_bw'
        target = 'AUTH_0123456789abcdef#2'
        request = self.factory.get('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target)
        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['dsl_filter'], dsl_filter)
        self.assertEqual(json_data['slo_name'], slo_name)
        self.assertEqual(json_data['target'], target)
        self.assertEqual(json_data['value'], '20')

    def test_slo_detail_when_does_not_exist(self):
        """ Test that a GET request to slo_detail() returns 404 if the slo does not exist """

        dsl_filter = 'bandwidth'
        slo_name = 'get_bw'
        target = 'inexistent'
        request = self.factory.get('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target)
        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_slo_ok(self):
        """ Test that a PUT request to slo_detail() returns OK """

        dsl_filter = 'bandwidth'
        slo_name = 'get_bw'
        target = 'AUTH_0123456789abcdef#2'
        new_value = '60'
        slo_data = {'value': new_value}
        request = self.factory.put('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target, slo_data, format='json')

        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the SLO was updated
        request = self.factory.get('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target)
        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(json_data['value'], new_value)

    def test_delete_slo_ok(self):
        """ Test that a DELETE request to slo_detail() returns OK """

        dsl_filter = 'bandwidth'
        slo_name = 'get_bw'
        target = 'AUTH_0123456789abcdef#2'
        request = self.factory.delete('/filters/slo/' + dsl_filter + '/' + slo_name + '/' + target)

        response = slo_detail(request, dsl_filter, slo_name, target)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the SLO was deleted
        request = self.factory.get('/filters/slos')
        response = slo_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 5)  # 6 --> 5


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

    def create_dependency(self):
        dependency_data = {'name': 'DependencyName', 'version': '1.0', 'permissions': '0755'}
        request = self.factory.post('/filters/dependencies', dependency_data, format='json')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_storage_policies(self):
        self.r.hmset("storage-policy:0", {'name': 'allnodes', 'default': 'yes', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:1", {'name': 'storage4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:2", {'name': 's0y1', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:3", {'name': 's3y4', 'default': 'no', 'policy_type': 'replication'})
        self.r.hmset("storage-policy:4", {'name': 's5y6', 'default': 'no', 'policy_type': 'replication'})

    def create_sample_bw_policies(self):
        # self.r.hmset('bw:AUTH_0123456789abcdef', {'2': '2000'})
        # self.r.hmset('bw:AUTH_abcdef0123456789', {'3': '3000'})
        self.r.set('SLO:bandwidth:get_bw:AUTH_0123456789abcdef#2', 20)
        self.r.set('SLO:bandwidth:put_bw:AUTH_0123456789abcdef#2', 30)
        self.r.set('SLO:bandwidth:ssync_bw:AUTH_0123456789abcdef#2', 50)
        self.r.set('SLO:bandwidth:get_bw:AUTH_abcdef0123456789#3', 10)
        self.r.set('SLO:bandwidth:put_bw:AUTH_abcdef0123456789#3', 15)
        self.r.set('SLO:bandwidth:ssync_bw:AUTH_abcdef0123456789#3', 25)