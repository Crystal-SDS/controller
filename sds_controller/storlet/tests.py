import json

import redis

from django.test import TestCase, RequestFactory, override_settings
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .views import storlet_list, storlet_detail, StorletData

# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL = redis.ConnectionPool(host='localhost', port=6379, db=10))
class StorletTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.factory = APIRequestFactory()

    def tearDown(self):
        r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        r.flushdb()

    def test_list_storlet(self):
        """
        Retrieve storlet list
        """
        # Create a storlet
        self.create_storlet()

        # Create an instance of a GET request.
        request = self.factory.get('/filters')
        response = storlet_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        storlets = json.loads(response.content)

        self.assertEqual(storlets[0]['name'], "FakeFilter")

    def test_delete_storlet(self):
        """
        Delete a storlet
        """
        # Create a storlet
        self.create_storlet()

        request = self.factory.delete('/filters/1')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")

    def test_update_storlet(self):
        """
        Update a storlet
        """
        self.create_storlet()

        filter_updated_data = {
            'name': 'FakeFilter', 'language': 'java', 'interface_version': '', 'dependencies': '',
            'object_metadata': '', 'main': 'com.example.UpdatedFakeMain', 'is_put': 'False', 'is_get': 'False',
            'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertEqual(storlets[0]['main'], 'com.example.UpdatedFakeMain')

    def test_update_storlet_with_invalid_request(self):
        self.create_storlet()

        filter_updated_data = {'wrongparam': 'dummy', 'language': 'java'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        request = self.factory.put('/filters/1', 'dummy test', content_type='text/plain')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # with name missing
        filter_updated_data = {
            'language': 'java', 'interface_version': '', 'dependencies': '',
            'object_metadata': '', 'main': 'com.example.UpdatedFakeMain', 'is_put': 'False', 'is_get': 'False',
            'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.put('/filters/1', filter_updated_data, format='json')
        response = storlet_detail(request, "1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_storlet(self):
        """
        Create 2 storlets
        """
        self.create_storlet()

        filter_data = {'name': 'SecondFilter', 'language': 'java', 'interface_version': '', 'dependencies': '',
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

        if (storlets[0]['id'] == "1"):
            storlet1 = storlets[0]
            storlet2 = storlets[1]
        else:
            storlet1 = storlets[0]
            storlet2 = storlets[1]

        self.assertEqual(storlet1['name'], 'FakeFilter')
        self.assertEqual(storlet2['name'], 'SecondFilter')

    def test_create_storlet_with_invalid_request(self):
        filter_data = {'wrongparam': 'dummy', 'language': 'java'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        request = self.factory.post('/filters/', 'dummy_text', content_type='text/plain')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # with name missing
        filter_data = {'language': 'java', 'interface_version': '', 'dependencies': '',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_storlet_data(self):
        self.create_storlet()

        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/1/data', {'file': fp})
            response = StorletData.as_view()(request, 1)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/filters')
        response = storlet_list(request)
        storlets = json.loads(response.content)
        self.assertTrue(len(storlets[0]['etag']) > 0)

    def test_upload_storlet_data_to_non_existent_storlet(self):
        self.create_storlet()

        with open('test_data/test.txt', 'r') as fp:
            request = self.factory.put('/filters/2/data', {'file': fp})
            response = StorletData.as_view()(request, 2)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'name': 'FakeFilter', 'language': 'java', 'interface_version': '', 'dependencies':'',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', filter_data, format='json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)