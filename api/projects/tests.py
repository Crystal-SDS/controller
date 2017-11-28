import calendar
import json
import mock
import os
import redis
import time

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory
from projects.views import add_projects_group, projects_group_detail, projects_groups_detail, projects, \
    create_docker_image, delete_docker_image


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class ProjectsTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.factory = APIRequestFactory()
        self.create_projects()
        self.create_tenant_group_1()
        self.create_nodes()

    def tearDown(self):
        self.r.flushdb()

    #
    # Projects
    #

    def test_get_projects_ok(self):
        request = self.factory.get('/projects')
        response = projects(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enabled_projects = json.loads(response.content)
        self.assertEqual(len(enabled_projects), 1)
        self.assertEqual(enabled_projects[0], '0123456789abcdef')

    @mock.patch('projects.views.create_docker_image')
    @mock.patch('projects.views.swift_client.post_account')
    @mock.patch('projects.views.swift_client.put_container')
    @mock.patch('projects.views.get_swift_url_and_token')
    @mock.patch('projects.views.get_admin_role_user_ids')
    @mock.patch('projects.views.get_keystone_admin_auth')
    @mock.patch('projects.views.get_project_list')
    def test_put_projects_ok(self, mock_get_project_list, mock_get_keystone_admin_auth, mock_get_admin_role_user_ids,
                             mock_get_swift_url_and_token, mock_put_container, mock_post_account, mock_create_docker_image):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA', 'abcdef0123456789': 'tenantB'}
        mock_get_swift_url_and_token.return_value = ('http://example.com/fakeurl', 'fakeToken',)
        mock_get_admin_role_user_ids.return_value = ('fakeId', 'fakeId', 'fakeName',)
        project_id = 'abcdef0123456789'
        request = self.factory.put('/projects' + project_id)
        response = projects(request, project_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(mock_put_container.call_count, 2)
        mock_post_account.assert_called_with('http://example.com/fakeurl', 'fakeToken', mock.ANY)
        mock_create_docker_image.assert_called_with(mock.ANY, project_id)

        # Check
        request = self.factory.get('/projects')
        response = projects(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enabled_projects = json.loads(response.content)
        self.assertEqual(len(enabled_projects), 2)
        self.assertTrue('abcdef0123456789' in enabled_projects)

    @mock.patch('projects.views.delete_docker_image')
    @mock.patch('projects.views.swift_client.post_account')
    @mock.patch('projects.views.swift_client.delete_container')
    @mock.patch('projects.views.get_swift_url_and_token')
    @mock.patch('projects.views.get_admin_role_user_ids')
    @mock.patch('projects.views.get_keystone_admin_auth')
    @mock.patch('projects.views.get_project_list')
    def test_delete_projects_ok(self, mock_get_project_list, mock_get_keystone_admin_auth, mock_get_admin_role_user_ids,
                                mock_get_swift_url_and_token, mock_delete_container, mock_post_account, mock_delete_docker_image):
        mock_get_project_list.return_value = {'0123456789abcdef': 'tenantA'}
        mock_get_swift_url_and_token.return_value = ('http://example.com/fakeurl', 'fakeToken',)
        mock_get_admin_role_user_ids.return_value = ('fakeId', 'fakeId', 'fakeName',)
        project_id = '0123456789abcdef'
        request = self.factory.delete('/projects' + project_id)
        response = projects(request, project_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(mock_delete_container.call_count, 2)
        mock_post_account.assert_called_with('http://example.com/fakeurl', 'fakeToken', mock.ANY)
        mock_delete_docker_image.assert_called_with(mock.ANY, project_id)

        # Check
        request = self.factory.get('/projects')
        response = projects(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enabled_projects = json.loads(response.content)
        self.assertEqual(len(enabled_projects), 0)

    def test_check_projects_ok(self):
        project_id = '0123456789abcdef'
        request = self.factory.post('/projects/' + project_id)
        response = projects(request, project_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_check_projects_non_existent(self):
        project_id = 'abcdef0123456789'
        request = self.factory.post('/projects/' + project_id)
        response = projects(request, project_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_projects_method_not_allowed(self):
        # HEAD method is not allowed
        request = self.factory.head('/projects')
        response = projects(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('projects.views.threading.Thread')
    def test_create_docker_image_ok(self, mock_thread):
        project_id = '0123456789abcdef'
        create_docker_image(self.r, project_id)
        self.assertEqual(mock_thread.call_count, 3)

    @mock.patch('projects.views.threading.Thread')
    def test_delete_docker_image_ok(self, mock_thread):
        project_id = '0123456789abcdef'
        delete_docker_image(self.r, project_id)
        self.assertEqual(mock_thread.call_count, 3)

    #
    # Tenant groups
    #

    def test_add_tenants_group_with_method_not_allowed(self):
        request = self.factory.delete('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_tenants_group_detail_with_method_not_allowed(self):
        gtenant_id = 1
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789'])}
        request = self.factory.post('/projects/groups/' + str(gtenant_id), tenant_group_data, format='json')
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gtenants_tenant_detail_with_method_not_allowed(self):
        gtenant_id = '1'
        tenant_id = '0123456789abcdef'
        request = self.factory.get('/projects/groups/' + gtenant_id + '/projects/' + tenant_id)
        response = projects_groups_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_tenants_group_ok(self):
        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        attached_projects = tenants_groups[0]['attached_projects']
        self.assertEqual(len(attached_projects), 2)  # 2 tenants in the group
        self.assertTrue('0123456789abcdef' in attached_projects)
        self.assertTrue('abcdef0123456789' in attached_projects)

    def test_create_tenant_group_ok(self):
        # Create a second tenant group
        tenant_group_data = {'name': 'group2', 'attached_projects': json.dumps(['tenant1_id', 'tenant2_id', 'tenant3_id'])}
        request = self.factory.post('/projects/groups', tenant_group_data, format='json')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 2)  # 2 groups
        for tenants_group in tenants_groups:
            if tenants_group['name'] == 'group2':
                attached_projects = tenants_group['attached_projects']
                self.assertEqual(len(attached_projects), 3)  # 3 tenants in the 2nd group
                self.assertTrue('tenant1_id' in attached_projects)
                self.assertTrue('tenant2_id' in attached_projects)
                self.assertTrue('tenant3_id' in attached_projects)

    def test_create_tenant_group_with_empty_data(self):
        # Create a second tenant group with empty data --> ERROR
        tenant_group_data = {}
        request = self.factory.post('/projects/groups', tenant_group_data, format='json')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_group_detail_ok(self):
        gtenant_id = '1'
        request = self.factory.get('/projects/groups/' + gtenant_id)
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = json.loads(response.content)
        self.assertEqual(response['name'], 'group1')
        tenant_list = response['attached_projects']
        self.assertEqual(len(tenant_list), 2)
        self.assertTrue('0123456789abcdef' in tenant_list)
        self.assertTrue('abcdef0123456789' in tenant_list)

    def test_tenant_group_detail_with_non_existent_id(self):
        gtenant_id = '2'
        request = self.factory.get('/projects/groups/' + gtenant_id)
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_tenant_group_ok(self):
        gtenant_id = '1'
        request = self.factory.delete('/projects/groups/' + gtenant_id)
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "[]")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 0)

    def test_delete_tenant_group_with_non_existent_id(self):
        gtenant_id = '2'
        request = self.factory.delete('/projects/groups/' + gtenant_id)
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check nothing was deleted
        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.content, "[]")
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups[0]['attached_projects']), 2)  # 2 tenants in the group

    def test_update_tenant_group_ok(self):
        gtenant_id = '1'
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789', '3333333333'])}
        request = self.factory.put('/projects/groups/' + gtenant_id, tenant_group_data, format='json')
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the object type was updated properly
        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)  # 1 group
        self.assertEqual(len(tenants_groups[0]['attached_projects']), 3)  # 3 tenants in the group
        self.assertTrue('0123456789abcdef' in tenants_groups[0]['attached_projects'])
        self.assertTrue('abcdef0123456789' in tenants_groups[0]['attached_projects'])
        self.assertTrue('3333333333' in tenants_groups[0]['attached_projects'])

    def test_update_tenant_group_with_non_existent_id(self):
        gtenant_id = '2'
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789', '3333333333'])}
        request = self.factory.put('/projects/groups/' + gtenant_id, tenant_group_data, format='json')
        response = projects_group_detail(request, gtenant_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_individual_tenant_from_group_ok(self):
        gtenant_id = '1'
        tenant_id = '0123456789abcdef'
        request = self.factory.delete('/projects/groups/' + gtenant_id + '/projects/' + tenant_id)
        response = projects_groups_detail(request, gtenant_id, tenant_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check delete was successful
        request = self.factory.get('/projects/groups')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tenants_groups = json.loads(response.content)
        self.assertEqual(len(tenants_groups), 1)
        self.assertEqual(len(tenants_groups[0]['attached_projects']), 1)
        self.assertFalse('0123456789abcdef' in tenants_groups[0]['attached_projects'])
        self.assertTrue('abcdef0123456789' in tenants_groups[0]['attached_projects'])



    #
    # Aux methods
    #

    def create_projects(self):
        self.r.lpush('projects_crystal_enabled', '0123456789abcdef')

    def create_tenant_group_1(self):
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789'])}
        request = self.factory.post('/projects/groups', tenant_group_data, format='json')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_nodes(self):
        self.r.hmset('proxy_node:controller',
                     {'ip': '192.168.2.1', 'last_ping': str(calendar.timegm(time.gmtime())), 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'ssh_access': 'False'})
        self.r.hmset('object_node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': str(calendar.timegm(time.gmtime())), 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'ssh_access': 'False'})
        self.r.hmset('object_node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': str(calendar.timegm(time.gmtime())), 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}', 'ssh_access': 'False'})
