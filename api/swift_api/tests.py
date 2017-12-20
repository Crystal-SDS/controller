import json
import mock
import redis

from django.conf import settings
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.test import APIRequestFactory

from swift_api.views import storage_policies, storage_policy_detail, storage_policy_disks, deploy_storage_policy, deployed_storage_policies, \
    locality_list, node_list, node_detail, regions, region_detail, zones, zone_detail, delete_storage_policy_disks, create_container, update_container, \
    load_swift_policies
import os


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   SWIFT_CFG_DEPLOY_DIR=os.path.join(os.getcwd(), 'test_data', 'deploy'))
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

    #
    # Storage Policies
    #

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

    @mock.patch('swift_api.views.RingBuilder')
    def test_storage_policies_post_ok(self, mock_ring_builder):
        data = {'policy_type': 'replication', 'partition_power': '5', 'replicas': '3', 'time': '10'}
        request = self.api_factory.post('/swift/storage_policies', data, format='json')
        response = storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_ring_builder.assert_called_with(5, 3, 10)
        mock_ring_builder.return_value.save.assert_called_with('/opt/crystal/swift/tmp/object-1.builder')

    def test_storage_policy_detail_get_ok(self):
        sp_id = '1'
        request = self.api_factory.get('/swift/storage_policy/' + sp_id)
        response = storage_policy_detail(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy_data = json.loads(response.content)
        self.assertEqual(policy_data['storage_policy_id'], sp_id)
        self.assertEqual(len(policy_data['devices']), 2)
        
    def test_storage_policy_detail_put_ok(self):
        sp_id = '1'
        data = {'name': 'storage4'}
        request = self.api_factory.put('/swift/storage_policy/' + sp_id, data, format='json')
        response = storage_policy_detail(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @mock.patch('swift_api.views.rsync_dir_with_nodes')
    def test_storage_policy_detail_delete_ok(self, mock_rsync):
        sp_id = '1'
        request = self.api_factory.delete('/swift/storage_policy/' + sp_id)
        response = storage_policy_detail(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_storage_policy_disks_get_ok(self):
        sp_id = '1'
        request = self.api_factory.get('/swift/storage_policy/' + sp_id + '/disk')
        response = storage_policy_disks(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        available_devices = json.loads(response.content)
        self.assertEqual(available_devices, [])

    @mock.patch('swift_api.views.RingBuilder.load')
    def test_storage_policy_disks_add_disk_ok(self, mock_ring_builder_load):
        mock_ring_builder_load.return_value.add_dev.return_value = '10'
        sp_id = '1'
        disk_data = "storagenode1:sdb2"
        request = self.api_factory.put('/swift/storage_policy/' + sp_id + '/disk', disk_data, format='json')
        response = storage_policy_disks(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ring_builder_load.assert_called_with('/opt/crystal/swift/tmp/object-1.builder')
        expected_dict = {'weight': 100, 'zone': 'Rack', 'ip': '192.168.2.2', 'region': 'data_center', 'device': 'sdb2', 'port': '6200'}
        mock_ring_builder_load.return_value.add_dev.assert_called_with(expected_dict)
        mock_ring_builder_load.return_value.save.assert_called_with('/opt/crystal/swift/tmp/object-1.builder')
        
    @mock.patch('swift_api.views.RingBuilder.load')
    def test_storage_policy_disk_delete(self, mock_ring_builder_load):
        sp_id = '1'
        disk_id = "storagenode1:sdb1"
        request = self.api_factory.delete('/swift/storage_policy/' + sp_id + '/disk/' + disk_id)
        response = delete_storage_policy_disks(request, sp_id, disk_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_storage_policy_disk_delete_sp_not_found(self):
        sp_id = '20'
        disk_id = "storagenode1:sdb1"
        request = self.api_factory.delete('/swift/storage_policy/' + sp_id + '/disk/' + disk_id)
        response = delete_storage_policy_disks(request, sp_id, disk_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        sp_id = '1'
        disk_id = "storagenode1:sdb5"
        request = self.api_factory.delete('/swift/storage_policy/' + sp_id + '/disk/' + disk_id)
        response = delete_storage_policy_disks(request, sp_id, disk_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            
    
    @mock.patch('swift_api.views.RingBuilder.load')
    @mock.patch('swift_api.views.copyfile')
    @mock.patch('swift_api.views.rsync_dir_with_nodes')
    def test_storage_policy_deploy(self, mock_rsync, mock_copyfile, mock_ring_builder_load):
        sp_id = '1'
        request = self.api_factory.post('/swift/storage_policy/' + sp_id + '/deploy/')
        response = deploy_storage_policy(request, sp_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ring_builder_load.assert_called_with('/opt/crystal/swift/tmp/object-1.builder')
        mock_ring_builder_load.return_value.save.assert_called_with('/opt/crystal/swift/tmp/object-1.builder')
        mock_ring_builder_load.return_value.get_ring.return_value.save.assert_called_with(os.path.join(os.getcwd(), 'test_data', 'deploy', 'object-1.ring.gz'))
        
    def test_storage_policies_deployed(self):
        request = self.api_factory.get('/swift/storage_policies/deployed')
        response = deployed_storage_policies(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sps = json.loads(response.content)
        self.assertEqual(len(sps), 1)
        self.assertEqual(sps[0]['name'], 'storage4')

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
    def test_regions_post_ok(self):
        data = {'name': 'data_center', 'description': 'Acme Data Center'}
        request = self.api_factory.post('/swift/regions/', data, format='json')
        response = regions(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regions_get_ok(self):
        request = self.api_factory.get('/swift/regions/')
        response = regions(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        region_items = json.loads(response.content)
        self.assertEqual(len(region_items), 2)
        self.assertEqual(region_items[0]['name'], 'data_center')

    def test_region_detail_delete_with_zone_assigned(self):
        region_id = '1'
        request = self.api_factory.delete('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_region_detail_delete_not_found(self):
        region_id = '3'
        request = self.api_factory.delete('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_region_detail_delete_ok(self):
        region_id = '2'
        request = self.api_factory.delete('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        request = self.api_factory.get('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_region_detail_update_ok(self):
        region_id = '2'
        request = self.api_factory.put('/swift/regions/' + region_id, {'name': 'data_center'}, format='json')
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
    def test_region_detail_get_ok(self):
        region_id = '2'
        request = self.api_factory.get('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_region_detail_get_not_found(self):
        region_id = '3'
        request = self.api_factory.get('/swift/regions/' + region_id)
        response = region_detail(request, region_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    
    def test_zones_post_ok(self):
        data = {'name': 'Rack', 'description': 'Dummy Rack: GbE Switch, 2 Proxies and 7 Storage Nodes', 'region': '1', 'zone_id': '1'}
        request = self.api_factory.post('/swift/zones/', data, format='json')
        response = zones(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_zones_get_ok(self):
        request = self.api_factory.get('/swift/zones/')
        response = zones(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zone_items = json.loads(response.content)
        self.assertEqual(len(zone_items), 1)
        self.assertEqual(zone_items[0]['name'], 'Rack')

    def test_zones_detail_get_ok(self):
        zone_id = '1'
        request = self.api_factory.get('/swift/zones/' + zone_id)
        response = zone_detail(request, zone_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zone = json.loads(response.content)
        self.assertEqual(zone['name'], 'Rack')

    def test_zones_detail_delete_ok(self):
        zone_id = '1'
        request = self.api_factory.delete('/swift/zones/' + zone_id)
        response = zone_detail(request, zone_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_zones_detail_update_ok(self):
        zone_id = '1'
        data = {'name': 'Rack', 'description': 'Dummy Rack: GbE Switch, 2 Proxies and 7 Storage Nodes', 'region': '1', 'zone_id': '1'}
        request = self.api_factory.put('/swift/zones/' + zone_id, data, format='json')
        response = zone_detail(request, zone_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    # Containers

    @mock.patch('swift_api.views.swift_client.put_container')
    def test_container_post(self, mock_swift_client):
        request = self.api_factory.post('/swift/projectid/container_name/create', {'header': 'foo'}, format='json')
        response = create_container(request, 'projectid', 'container_name')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch('swift_api.views.swift_client')
    @mock.patch('swift_api.views.os')
    @mock.patch('swift_api.views.open')
    def test_container_update(self, mock_open, mock_os, mock_swift_client):
        request = self.api_factory.put('/swift/projectid/container_name/update', 'foo', format='json')
        mock_swift_client.get_container.return_value = {'header': 'foo'}, [{'name': 'objname', 'content_type': 'text', 'headers': 'foo'}]
        mock_swift_client.get_object.return_value = {'header': 'foo'}, 'body'
        response = update_container(request, 'projectid', 'container_name')        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch('swift_api.views.ConfigParser')
    @mock.patch('swift_api.views.RingBuilder')
    @mock.patch('swift_api.views.glob')
    @mock.patch('swift_api.views.paramiko.SSHClient')
    def test_load_swift_policies(self, mock_ssh_client, mock_glob, mock_ring_builder, mock_config_parser):
        request = self.api_factory.post('/swift/storage_policies/load')
        mock_glob.glob.return_value = ['foo-1.file']
        mock_ssh_client.return_value.listdir.return_value = ['object.builder']
        mock_config_parser.has_section.return_value = True
        mock_config_parser.has_section.return_value = False
        response = load_swift_policies(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    
    #
    # Aux functions
    #
    def create_storage_policies(self):
        devices = [["storagenode1:sdb1", 0], ["storagenode2:sdb1", 1]]
        self.r.hmset("storage-policy:0", {'name': 'allnodes', 'default': 'yes', 'policy_type': 'replication',
                                          'devices': json.dumps(devices), 'deprecated': 'false'})
        self.r.hmset("storage-policy:1", {'name': 'storage4', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices), 'deprecated': 'false'})
        self.r.hmset("storage-policy:2", {'name': 's0y1', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices), 'deprecated': 'false'})
        self.r.hmset("storage-policy:3", {'name': 's3y4', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices), 'deprecated': 'false'})
        self.r.hmset("storage-policy:4", {'name': 's5y6', 'default': 'no', 'policy_type': 'replication',
                                          'devices': json.dumps(devices), 'deprecated': 'false'})

    def create_nodes(self):
        self.r.hmset('proxy_node:controller',
                     {'ip': '192.168.2.1', 'last_ping': '1467623304.332646', 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False', 'ssh_username': 'user', 'ssh_password': 'pass'})
        self.r.hmset('object_node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False', 'ssh_username': 'user', 'ssh_password': 'pass'})
        self.r.hmset('object_node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'region_id': 1, 'zone_id': 1,
                      'ssh_access': 'False', 'ssh_username': 'user', 'ssh_password': 'pass'})

    def create_regions_and_zones(self):
        self.r.set('regions:id', 2)
        self.r.hmset('region:1', {'name': 'data_center', 'description': 'Acme Data Center'})
        self.r.hmset('region:2', {'name': 'data_center', 'description': 'Acme Data Center'})
        self.r.set('zones:id', 1)
        self.r.hmset('zone:1', {'name': 'Rack', 'description': 'Dummy Rack: GbE Switch, 2 Proxies and 7 Storage Nodes',
                                'region': '1', 'zone_id': '1'})
