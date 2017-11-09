import json
import os

import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory
from projects.views import add_projects_group, projects_group_detail, projects_groups_detail


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
        self.create_tenant_group_1()

    def tearDown(self):
        self.r.flushdb()

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

    def create_tenant_group_1(self):
        tenant_group_data = {'name': 'group1', 'attached_projects': json.dumps(['0123456789abcdef', 'abcdef0123456789'])}
        request = self.factory.post('/projects/groups', tenant_group_data, format='json')
        response = add_projects_group(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)