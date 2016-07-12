import json

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import dependency_list, dependency_detail, storlet_list, storlet_detail, storlet_list_deployed, storlet_deploy, StorletData


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class StorletTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.factory = APIRequestFactory()
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        self.create_storlet()
        self.create_dependency()

    def tearDown(self):
        self.r.flushdb()

    def test_list_storlet_ok(self):
        """
        Retrieve storlet list
        """
        # Create an instance of a GET request.
        request = self.factory.get('/filters')
        response = storlet_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        storlets = json.loads(response.content)
        self.assertEqual(storlets[0]['main'], "com.example.FakeMain")

    def test_delete_storlet_ok(self):
        """
        Delete a storlet
        """
        request = self.factory.delete('/filters/1')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_delete_storlet_if_not_exists(self):
        """
        Delete a non existent storlet
        """
        request = self.factory.delete('/filters/2')
        response = storlet_detail(request, "2")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_storlet_ok(self):
        """
        Update a storlet
        """
        filter_updated_data = {
            'filter_type': 'java', 'interface_version': '', 'dependencies': '',
            'object_metadata': '', 'main': 'com.example.UpdatedFakeMain', 'is_put': 'False', 'is_get': 'False',
            'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(storlets[0]['main'], 'com.example.UpdatedFakeMain')

    def test_update_storlet_with_invalid_requests(self):

        # Invalid parameter
        filter_updated_data = {'wrongparam': 'dummy', 'filter_type': 'java'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Wrong content type
        request = self.factory.put('/filters/1', 'dummy test', content_type='text/plain')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # With name missing
        filter_updated_data = {
            'filter_name': 'FakeFilter', 'filter_type': 'java', 'interface_version': '', 'dependencies': '',
            'object_metadata': '', 'main': 'com.example.UpdatedFakeMain', 'is_put': 'False', 'is_get': 'False',
            'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_storlet_ok(self):
        """
        Create 2 storlets
        """

        # Create a second storlet
        filter_data = {'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.SecondMain', 'is_put': 'False',
                       'is_get': 'False', 'has_reverse': 'False', 'execution_server': 'proxy',
                       'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(len(storlets), 2)

        if storlets[0]['id'] == "1":
            storlet1 = storlets[0]
            storlet2 = storlets[1]
        else:
            storlet1 = storlets[1]
            storlet2 = storlets[0]
        self.assertEqual(storlet1['main'], 'com.example.FakeMain')
        self.assertEqual(storlet2['main'], 'com.example.SecondMain')

    def test_create_storlets_are_sorted_by_id(self):
        """
        Create several storlets and check they are returned as a sorted list by identifier
        """

        # Create a second storlet
        filter_data = {'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.SecondMain', 'is_put': 'False',
                       'is_get': 'False', 'has_reverse': 'False', 'execution_server': 'proxy',
                       'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create a third storlet
        filter_data = {'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.ThirdMain', 'is_put': 'False',
                       'is_get': 'False', 'has_reverse': 'False', 'execution_server': 'proxy',
                       'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create a Fourth storlet
        filter_data = {'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FourthMain', 'is_put': 'False',
                       'is_get': 'False', 'has_reverse': 'False', 'execution_server': 'proxy',
                       'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(len(storlets), 4)
        self.assertEqual(storlets[0]['main'], 'com.example.FakeMain')
        self.assertEqual(storlets[1]['main'], 'com.example.SecondMain')
        self.assertEqual(storlets[2]['main'], 'com.example.ThirdMain')
        self.assertEqual(storlets[3]['main'], 'com.example.FourthMain')

    def test_create_storlet_with_invalid_request(self):
        # Invalid param
        filter_data = {'wrongparam': 'dummy', 'filter_type': 'java'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Wrong content type
        request = self.factory.post('/filters/', 'dummy_text', content_type='text/plain')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # with name present
        filter_data = {'filter_name': 'secondFilter', 'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_storlet_data_ok(self):
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            response = StorletData.as_view()(request, 1)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertTrue(len(storlets[0]['etag']) > 0)

    def test_upload_storlet_data_to_non_existent_storlet(self):
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/2/data', {'file': fp})
            response = StorletData.as_view()(request, 2)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_storlet_list_deployed_for_empty_tenant(self):
        request = self.factory.get('/filters/0123456789abcdef/deploy')
        response = storlet_list_deployed(request, '0123456789abcdef')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def mock_put_object_status_created(url, token=None, container=None, name=None, contents=None,
                                       content_length=None, etag=None, chunk_size=None,
                                       content_type=None, headers=None, http_conn=None, proxy=None,
                                       query_string=None, response_dict=None):
        response_dict['status'] = status.HTTP_201_CREATED

    @mock.patch('storlet.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def test_storlet_deploy_to_project_ok(self, mock_put_object):
        # Upload a filter for the storlet 1
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            StorletData.as_view()(request, 1)

        # Call storlet_deploy
        data = {"filter_id": "1", "target_id": "0123456789abcdef",
                "execution_server": "proxy", "execution_server_reverse": "proxy",
                "object_type": "", "object_size": "", "params": ""}

        request = self.factory.put('/filters/0123456789abcdef/deploy/1', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = storlet_deploy(request, "1", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_put_object.assert_called_with(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_0123456789abcdef",
                                           'fake_token', "storlet", "test.txt", mock.ANY, mock.ANY, mock.ANY,
                                           mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
        self.assertTrue(self.r.hexists("pipeline:AUTH_0123456789abcdef", "1"))
        dumped_data = self.r.hget("pipeline:AUTH_0123456789abcdef", "1")
        json_data = json.loads(dumped_data)
        self.assertEqual(json_data["filter_name"], "test.txt")

    @mock.patch('storlet.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    def test_storlet_deploy_to_project_and_container_ok(self, mock_put_object):
        # Upload a filter for the storlet 1
        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            StorletData.as_view()(request, 1)

        # Call storlet_deploy
        data = {"filter_id": "1", "target_id": "0123456789abcdef",
                "execution_server": "proxy", "execution_server_reverse": "proxy",
                "object_type": "", "object_size": "", "params": ""}

        request = self.factory.put('/filters/0123456789abcdef/container1/deploy/1', data, format='json')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = storlet_deploy(request, "1", "0123456789abcdef", "container1")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_put_object.assert_called_with(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_0123456789abcdef",
                                           'fake_token', "storlet", "test.txt", mock.ANY, mock.ANY, mock.ANY,
                                           mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
        self.assertTrue(self.r.hexists("pipeline:AUTH_0123456789abcdef:container1", "1"))
        dumped_data = self.r.hget("pipeline:AUTH_0123456789abcdef:container1", "1")
        json_data = json.loads(dumped_data)
        self.assertEqual(json_data["filter_name"], "test.txt")

    def test_storlet_deploy_without_auth_token(self):
        request = self.factory.put('/filters/0123456789abcdef/deploy/1', {"policy_id": "1"}, format='json')
        response = storlet_deploy(request, "1", "0123456789abcdef")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # def _test_storlet_undeploy_for_non_existent_storlet(self):
    #     # Filter 2 does not exist
    #     request = self.factory.put('/filters/0123456789abcdef/undeploy/2')
    #     response = storlet_undeploy(request, '2', '0123456789abcdef')
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    #
    # def _test_storlet_undeploy_for_non_deployed_storlet_and_project(self):
    #     request = self.factory.put('/filters/0123456789abcdef/undeploy/1')
    #     response = storlet_undeploy(request, '1', '0123456789abcdef')
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # @mock.patch('storlet.views.swift_client.put_object', side_effect=mock_put_object_status_created)
    # def test_storlet_undeploy_without_auth_token(self, mock_put_object):
    #     # Upload a filter for the storlet 1
    #     with open('test_data/test.txt', 'r') as fp:
    #         request = self.factory.put('/filters/1/data', {'file': fp})
    #         response = StorletData.as_view()(request, 1)
    #
    #     # Call storlet_deploy
    #     request = self.factory.put('/filters/0123456789abcdef/deploy/1', {"policy_id": "1"}, format='json')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
    #     response = storlet_deploy(request, "1", "0123456789abcdef")
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     mock_put_object.assert_called_with(settings.SWIFT_URL + settings.SWIFT_API_VERSION + "/AUTH_0123456789abcdef",
    #                                        'fake_token', "storlet", "FakeFilter", mock.ANY, mock.ANY, mock.ANY,
    #                                        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
    #     self.assertTrue(self.r.hexists("pipeline:AUTH_0123456789abcdef", "1"))
    #     dumped_data = self.r.hget("pipeline:AUTH_0123456789abcdef", "1")
    #     json_data = json.loads(dumped_data)
    #     self.assertEqual(json_data["filter_name"], "FakeFilter")
    #
    #     # Try to undeploy without auth token
    #     request = self.factory.put('/filters/0123456789abcdef/undeploy/1')
    #     response = storlet_undeploy(request, "1", "0123456789abcdef")
    #     print response
    #     self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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



    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'filter_type': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_dependency(self):
        dependency_data = {'name': 'DependencyName', 'version': '1.0', 'permissions': '0755'}
        request = self.factory.post('/filters/dependencies', dependency_data, format='json')
        response = dependency_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
