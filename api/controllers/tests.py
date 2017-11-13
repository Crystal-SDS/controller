import json
import os

import mock
import redis
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from api.common import controller_actors
from controllers.views import controller_list, controller_detail, ControllerData, create_instance, instance_detail, \
    instances_list, start_controller_instance, stop_controller_instance


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10),
                   STORLET_FILTERS_DIR=os.path.join("/tmp", "crystal", "storlet_filters"),
                   WORKLOAD_METRICS_DIR=os.path.join("/tmp", "crystal", "workload_metrics"),
                   GLOBAL_CONTROLLERS_DIR=os.path.join("/tmp", "crystal", "global_controllers"))
class ControllersTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        # Using rest_framework's APIRequestFactory: http://www.django-rest-framework.org/api-guide/testing/
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

        self.factory = APIRequestFactory()

        self.create_global_controllers()

    def tearDown(self):
        self.r.flushdb()


    #
    # controller_list()/controller_detail()
    #

    def test_controller_list_with_method_not_allowed(self):
        request = self.factory.delete('/controllers')
        response = controller_list(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_controller_detail_with_method_not_allowed(self):
        gc_id = '1'
        request = self.factory.post('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_controller_list_ok(self):
        request = self.factory.get('/controllers')
        response = controller_list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        global_controllers = json.loads(response.content)
        self.assertEqual(global_controllers[0]['class_name'], "MinTenantSLOGlobalSpareBWShare")

    def test_controller_detail_get_ok(self):
        gc_id = '1'
        request = self.factory.get('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)

        global_controller = json.loads(response.content)
        self.assertEqual(global_controller['class_name'], "MinTenantSLOGlobalSpareBWShare")

    def test_controller_detail_put_ok(self):
        gc_id = '1'
        controller_data = {'description': 'New description'}
        request = self.factory.put('/controllers/' + gc_id, controller_data, format='json')
        response = controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check description has been updated
        request = self.factory.get('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)
        controller = json.loads(response.content)
        self.assertEqual(controller['description'], 'New description')

    def test_controller_detail_delete_ok(self):
        gc_id = '1'
        request = self.factory.delete('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify controller is deleted
        request = self.factory.get('/controllers')
        response = controller_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        global_controllers = json.loads(response.content)
        self.assertEqual(len(global_controllers), 0)

    @mock.patch('controllers.views.stop_controller_instance')
    @mock.patch('controllers.views.start_controller_instance')
    def test_controller_create_instance_start_stop_ok(self, mock_start_controller_instance, mock_stop_controller_instance):
        gc_id = '1'
        controller_data = {'controller': gc_id, 'parameters': ''}
        request = self.factory.post('/controllers/instance', controller_data, format='json')
        response = create_instance(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check created
        request = self.factory.get('/controllers/instances')
        response = instances_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instances_list_data = json.loads(response.content)
        self.assertEqual(len(instances_list_data), 1)

        # Check detail
        instance_id = '1'
        request = self.factory.get('/controllers/instance/' + instance_id)
        response = instance_detail(request, instance_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance_data = json.loads(response.content)
        self.assertEqual(instance_data['controller'], '1')

        # Start instance
        instance_id = '1'
        controller_data = {'status': 'Running'}
        request = self.factory.put('/controllers/instance/' + instance_id, controller_data, format='json')
        response = instance_detail(request, instance_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_start_controller_instance.called)

        # Stop instance
        controller_data = {'status': 'Stopped'}
        request = self.factory.put('/controllers/instance/' + instance_id, controller_data, format='json')
        response = instance_detail(request, instance_id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_stop_controller_instance.called)

    def test_controller_delete_instance_ok(self):
        gc_id = '1'
        controller_data = {'controller': gc_id, 'parameters': ''}
        request = self.factory.post('/controllers/instance', controller_data, format='json')
        response = create_instance(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        instance_id = '1'
        request = self.factory.delete('/controllers/instance' + instance_id)
        response = instance_detail(request, instance_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.r.exists('controller_instances:id'))

    def test_controller_data_view_with_method_not_allowed(self):
        # No DELETE method for this API call
        request = self.factory.delete('/controllers/data/')
        response = ControllerData.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_controller_ok(self):
        with open('test_data/test.py', 'r') as fp:
            metadata = {'class_name': 'TestClass', 'enabled': 'False', 'description': 'test controller', 'type': 'get'}
            request = self.factory.post('/controllers/data/', {'file': fp, 'metadata': json.dumps(metadata)})
            response = ControllerData.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        global_controller = json.loads(response.content)

        self.assertEqual(global_controller['id'], 2)
        self.assertEqual(global_controller['enabled'], 'False')
        self.assertEqual(global_controller['controller_name'], 'test.py')

        # check the global controller has been created
        gc_id = '2'
        request = self.factory.get('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gc_data = json.loads(response.content)
        self.assertEqual(gc_data['controller_name'], 'test.py')

    def test_update_controller_with_put_ok(self):
        gc_id = '1'
        with open('test_data/test.py', 'r') as fp:
            request = self.factory.put('/controllers/' + gc_id + '/data', {'file': fp})
            response = ControllerData.as_view()(request, gc_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check the global controller has been updated
        request = self.factory.get('/controllers/' + gc_id)
        response = controller_detail(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gc_data = json.loads(response.content)
        self.assertEqual(gc_data['controller_name'], 'test.py')

    def test_download_controller_not_found(self):
        gc_id = '1'
        request = self.factory.get('/controllers/' + gc_id + '/data')
        response = ControllerData.as_view()(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('controllers.views.os.path.join')
    def test_download_controller_ok(self, mock_os_path_join):
        mock_os_path_join.return_value = 'test_data/test.py'
        gc_id = '1'
        request = self.factory.get('/controllers/' + gc_id + '/data')
        response = ControllerData.as_view()(request, gc_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Length'], '11')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=test.py')

    @mock.patch('controllers.views.create_local_host')
    def test_start_stop_controller_instance(self, mock_create_local_host):
        # First: start controller instance
        instance_id = '1'
        controller_name = 'FakeControllerName'
        controller_class_name = 'controllersclass'
        parameters = 'paramA=AAA, paramB=BBB'
        start_controller_instance(instance_id, controller_name, controller_class_name, parameters)
        self.assertTrue(mock_create_local_host.called)
        self.assertTrue(mock_create_local_host.return_value.spawn.called)

        self.assertEqual(len(controller_actors), 1)

        # Then: stop controller instance
        stop_controller_instance(instance_id)
        self.assertEqual(len(controller_actors), 0)

    #
    # Aux methods
    #

    def create_global_controllers(self):
        self.r.incr("controllers:id")  # setting autoincrement to 1
        self.r.hmset('controller:1', {'class_name': 'MinTenantSLOGlobalSpareBWShare',
                                      'controller_name': 'min_slo_tenant_global_share_spare_bw_v2.py',
                                      'valid_parameters': 'method={put|get}', 'id': '1', 'instances': 0,
                                      'enabled': 'False', 'description': 'Fake description'})