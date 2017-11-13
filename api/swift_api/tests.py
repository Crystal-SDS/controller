import json
import mock
import redis

from django.conf import settings
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.test import APIRequestFactory

from swift_api.views import storage_policies, locality_list, node_list, node_detail, regions


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class SwiftTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.api_factory = APIRequestFactory()
        self.simple_factory = RequestFactory()
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        # initializations
        self.create_storage_policies()
        self.create_nodes()
        self.create_regions_and_zones()

    def tearDown(self):
        self.r.flushdb()

    def test_storage_policies_with_method_not_allowed(self):
        """ Test that PUT requests to storage_policies() return METHOD_NOT_ALLOWED """

        request = self.api_factory.put('/swift/storage_policies')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_locality_list_with_method_not_allowed(self):
        """ Test that POST requests to locality_list() return METHOD_NOT_ALLOWED """
        request = self.api_factory.post('/swift/locality/123456789abcdef/container1/object1.txt')
        response = locality_list(request, '123456789abcdef', 'container1', 'object1.txt')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_storage_policy_list_ok(self):
        """ Test that GET requests to storage_policy_list() return METHOD_NOT_ALLOWED """

        request = self.api_factory.get('/swift/storage_policies')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storage_policies_json = json.loads(response.content)
        self.assertEqual(len(storage_policies_json), 5)

    #
    # Nodes
    #

    def test_node_list_with_method_not_allowed(self):
        request = self.api_factory.delete('/swift/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_nodes_ok(self):
        request = self.api_factory.get('/swift/nodes')
        response = node_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")

        nodes = json.loads(response.content)
        self.assertEqual(len(nodes), 3)
        node_names = [node['name'] for node in nodes]
        self.assertTrue('controller' in node_names)
        self.assertTrue('storagenode1' in node_names)
        self.assertTrue('storagenode2' in node_names)
        a_device = nodes[0]['devices'].keys()[0]
        self.assertIsNotNone(nodes[0]['devices'][a_device]['free'])

    def test_node_detail_with_method_not_allowed(self):
        server_type = 'object'
        node_id = 'storagenode1'
        # POST is not supported
        request = self.api_factory.post('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_node_detail_ok(self):
        server_type = 'object'
        node_id = 'storagenode1'
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        node = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(node['name'], 'storagenode1')

    def test_get_node_detail_with_non_existent_server_name(self):
        server_type = 'object'
        node_id = 'storagenode100000'
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_node_detail_ok(self):
        server_type = 'object'
        node_id = 'storagenode1'
        request = self.api_factory.delete('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify it was deleted
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_node_detail_not_found(self):
        server_type = 'object'
        node_id = 'storagenode100000'
        request = self.api_factory.delete('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_node_detail_not_found(self):
        server_type = 'object'
        node_id = 'storagenode100000'
        request = self.api_factory.put('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('swift_api.views.paramiko.SSHClient')
    def test_put_node_detail_ok(self, mock_ssh_client):
        server_type = 'object'
        node_id = 'storagenode1'
        data = {'ssh_username': 'admin', 'ssh_password': 's3cr3t'}
        request = self.api_factory.put('/swift/nodes/' + server_type + '/' + node_id, data, format='json')
        response = node_detail(request, server_type, node_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_ssh_client.assert_called()

        # Check ssh settings are stored:
        request = self.api_factory.get('/swift/nodes/' + server_type + '/' + node_id)
        response = node_detail(request, server_type, node_id)
        node = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(node['name'], 'storagenode1')
        self.assertEqual(node['ssh_access'], 'True')
        self.assertEqual(node['ssh_username'], 'admin')



    # Regions / Zones

    def test_regions_get_ok(self):
        request = self.api_factory.get('/swift/regions/')
        response = regions(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        region_items = json.loads(response.content)
        self.assertEqual(len(region_items), 1)
        self.assertEqual(region_items[0]['name'], 'data_center')

    #
    # Aux functions
    #

    def create_storage_policies(self):
        devices = ["storagenode1:sdb1", "storagenode2:sdb1"]
        self.r.hmset("storage-policy:0", {'name': 'allnodes', 'default': 'yes', 'policy_type': 'replication',
                                          'devices': json.dumps(devices)})
        self.r.hmset("storage-policy:1", {'name': 'storage4', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices)})
        self.r.hmset("storage-policy:2", {'name': 's0y1', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices)})
        self.r.hmset("storage-policy:3", {'name': 's3y4', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices)})
        self.r.hmset("storage-policy:4", {'name': 's5y6', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices)})

    def create_nodes(self):
        self.r.hmset('proxy_node:controller',
                     {'ip': '192.168.2.1', 'last_ping': '1467623304.332646', 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False'})
        self.r.hmset('object_node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False'})
        self.r.hmset('object_node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False'})

    def create_regions_and_zones(self):
        self.r.set('regions:id', 1)
        self.r.hmset('region:1', {'name': 'data_center', 'description': 'Acme Data Center'})
        self.r.set('zones:id', 1)
        self.r.hmset('zone:1', {'name': 'Rack', 'description': 'Dummy Rack: GbE Switch, 2 Proxies and 7 Storage Nodes',
                                'regions': '1', 'zone_id': '1'})
