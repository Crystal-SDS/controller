import json

import redis

from django.test import TestCase, RequestFactory, override_settings
from django.conf import settings

from .views import storlet_list

# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL = redis.ConnectionPool(host='localhost', port=6379, db=10))
class StorletTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()

    def tearDown(self):
        r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        #r.flushdb()

    def test_list_storlet(self):
        """..."""

        # Create a storlet
        self.create_storlet()

        # Create an instance of a GET request.
        request = self.factory.get('/filters')
        response = storlet_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, [])

        storlets = json.loads(response.content)

        self.assertEqual(storlets[0]['name'], "FakeFilter")

    #
    # Aux methods
    #

    def create_storlet(self):
        filter_data = {'name': 'FakeFilter', 'language': 'java', 'interface_version': '', 'dependencies':'',
                       'object_metadata': '', 'main': 'com.example.FakeMain', 'is_put': 'False', 'is_get': 'False',
                       'has_reverse': 'False', 'execution_server': 'proxy', 'execution_server_reverse': 'proxy'}
        request = self.factory.post('/filters/', json.dumps(filter_data), 'application/json')
        response = storlet_list(request)
        self.assertEqual(response.status_code, 201) # created