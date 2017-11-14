import calendar
import time
import mock
import redis
from datetime import timedelta
from django.conf import settings
from django.core.urlresolvers import resolve
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from .common import get_all_registered_nodes, remove_extra_whitespaces, to_json_bools, rsync_dir_with_nodes, get_project_list, get_keystone_admin_auth
from .exceptions import FileSynchronizationException
from .startup import run as startup_run
from .middleware import CrystalMiddleware


# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class MainTestCase(TestCase):
    def setUp(self):
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        self.create_nodes()
        self.factory = APIRequestFactory()

    def tearDown(self):
        self.r.flushdb()

    def test_remove_extra_whitespaces_ok(self):
        ret = remove_extra_whitespaces("a  b c   d e     f")
        self.assertEqual(ret, "a b c d e f")

        ret = remove_extra_whitespaces("      a  b c   d e     f  ")
        self.assertEqual(ret, "a b c d e f")

    def test_get_all_registered_nodes_ok(self):
        node_list = get_all_registered_nodes()
        self.assertEqual(len(node_list), 3)
        sorted_list = sorted(node_list, key=lambda node: node['name'])
        self.assertEqual(sorted_list[0]['name'], 'controller')
        self.assertEqual(sorted_list[1]['name'], 'storagenode1')
        self.assertEqual(sorted_list[2]['name'], 'storagenode2')

    def test_to_json_bools_ok(self):
        bdict = {'a': 'True', 'b': 'False', 'c': 'True', 'd': 'False'}
        to_json_bools(bdict, 'a', 'b', 'c')
        self.assertEqual(bdict['a'], True)
        self.assertNotEqual(bdict['a'], 'True')
        self.assertEqual(bdict['b'], False)
        self.assertNotEqual(bdict['b'], 'False')
        self.assertEqual(bdict['c'], True)
        self.assertNotEqual(bdict['c'], 'True')
        self.assertEqual(bdict['d'], 'False')
        self.assertNotEqual(bdict['d'], False)

    @mock.patch('api.common.threading.Thread')
    def test_rsync_dir_with_nodes_ok(self, mock_thread):
        self.configure_usernames_and_passwords_for_nodes()
        rsync_dir_with_nodes(settings.WORKLOAD_METRICS_DIR)
        self.assertEqual(mock_thread.call_count, 3)

    def test_rsync_dir_with_nodes_when_username_and_password_not_present(self):
        with self.assertRaises(FileSynchronizationException):
            rsync_dir_with_nodes(settings.WORKLOAD_METRICS_DIR)

    # @mock.patch('api.common_utils.get_keystone_admin_auth')
    # def test_is_valid_request_new_valid_token(self, mock_keystone_admin_auth):
    #     not_expired_admin_token = FakeTokenData((datetime.utcnow() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    #                                             {'roles': [{'name': 'admin'}, {'name': '_member_'}]})
    #     mock_keystone_admin_auth.return_value.tokens.validate.return_value = not_expired_admin_token
    #     request = self.factory.get('/')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'new_not_expired_token'
    #     resp = get_token_connection(request)
    #     self.assertEquals(resp, 'new_not_expired_token')
    #     self.assertTrue(mock_keystone_admin_auth.called)
    #     mock_keystone_admin_auth.reset_mock()
    #
    #     Successive calls should not invoke keystone
    #     request = self.factory.get('/')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'new_not_expired_token'
    #     resp = get_token_connection(request)
    #     self.assertEquals(resp, 'new_not_expired_token')
    #     self.assertFalse(mock_keystone_admin_auth.called)

    # @mock.patch('api.common_utils.get_keystone_admin_auth')
    # def test_is_valid_request_new_expired_token(self, mock_keystone_admin_auth):
    #     not_expired_admin_token = FakeTokenData((datetime.utcnow() - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    #                                             {'roles': [{'name': 'admin'}, {'name': '_member_'}]})
    #     mock_keystone_admin_auth.return_value.tokens.validate.return_value = not_expired_admin_token
    #     request = self.factory.get('/')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'expired_token'
    #     resp = get_token_connection(request)
    #     self.assertFalse(resp)

    # @mock.patch('api.common_utils.get_keystone_admin_auth')
    # def test_is_valid_request_not_admin(self, mock_keystone_admin_auth):
    #     not_expired_admin_token = FakeTokenData((datetime.utcnow() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    #                                             {'roles': [{'name': '_member_'}]})
    #     mock_keystone_admin_auth.return_value.tokens.validate.return_value = not_expired_admin_token
    #     request = self.factory.get('/')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'not_admin_token'
    #     resp = get_token_connection(request)
    #     self.assertFalse(resp)

    # @mock.patch('api.common_utils.get_keystone_admin_auth')
    # def test_is_valid_request_raises_exception(self, mock_keystone_admin_auth):
    #     mock_keystone_admin_auth.return_value.tokens.validate.side_effect = Exception()
    #     request = self.factory.get('/')
    #     request.META['HTTP_X_AUTH_TOKEN'] = 'token'
    #     resp = get_token_connection(request)
    #     self.assertFalse(resp)

    @mock.patch('api.common.get_keystone_admin_auth')
    def test_get_project_list_ok(self, mock_keystone_admin_auth):
        fake_tenants_list = [FakeTenantData('1234567890abcdef', 'tenantA'), FakeTenantData('abcdef1234567890', 'tenantB')]
        mock_keystone_admin_auth.return_value.projects.list.return_value = fake_tenants_list
        resp = get_project_list()
        self.assertEquals(resp['1234567890abcdef'], 'tenantA')
        self.assertEquals(resp['abcdef1234567890'], 'tenantB')

    @override_settings(MANAGEMENT_ACCOUNT='mng_account', MANAGEMENT_ADMIN_USERNAME='mng_username', MANAGEMENT_ADMIN_PASSWORD='mng_pw',
                       KEYSTONE_ADMIN_URL='http://localhost:35357/v3')
    @mock.patch('api.common.client.Client')
    @mock.patch('api.common.session.Session')
    @mock.patch('api.common.v3.Password')
    def test_get_keystone_admin_auth_ok(self, mock_password, mock_session, mock_keystone_client):
        get_keystone_admin_auth()
        mock_password.assert_called_with(auth_url='http://localhost:35357/v3', username='mng_username', password='mng_pw',
                                         project_name='mng_account', user_domain_id='default', project_domain_id='default')
        mock_session.assert_called()
        mock_keystone_client.assert_called()

    @mock.patch('api.startup.redis.Redis')
    def test_startup_run_ok(self, mock_startup_redis):
        self.create_startup_fixtures()
        # Mocking redis to use DB=10 (in startup.py, settings are imported directly from ./settings.py instead of using django.conf)
        mock_startup_redis.return_value = self.r
        startup_run()
        self.assertEquals(self.r.hget('workload_metric:1', 'status'), 'Stopped')
        self.assertEquals(self.r.hget('workload_metric:2', 'status'), 'Stopped')
        self.assertFalse(self.r.exists('metric:metric1'))
        self.assertFalse(self.r.exists('metric:metric2'))
        self.assertEquals(self.r.hget('policy:1', 'status'), 'Stopped')
        self.assertEquals(self.r.hget('policy:2', 'status'), 'Stopped')

    #
    # URL tests
    #

    def test_urls(self):
        resolver = resolve('/filters/')
        self.assertEqual(resolver.view_name, 'filters.views.filter_list')

        resolver = resolve('/filters/123')
        self.assertEqual(resolver.view_name, 'filters.views.filter_detail')
        self.assertEqual(resolver.kwargs, {'filter_id': '123'})

        resolver = resolve('/filters/123/data')
        self.assertEqual(resolver.view_name, 'filters.views.FilterData')
        self.assertEqual(resolver.kwargs, {'filter_id': '123'})

        resolver = resolve('/swift/nodes/')
        self.assertEqual(resolver.view_name, 'swift_api.views.node_list')

        resolver = resolve('/swift/nodes/object/node1')
        self.assertEqual(resolver.view_name, 'swift_api.views.node_detail')
        self.assertEqual(resolver.kwargs, {'server_type': 'object', 'node_id': 'node1'})

    #
    # Crystal Middleware tests
    #

    def test_middleware_no_token_header(self):
        cm = CrystalMiddleware()

        request = self.factory.get('/filters')
        response = cm.process_request(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('api.middleware.get_keystone_admin_auth')
    def test_middleware_with_new_token_ok(self, mock_get_keystone_admin_auth):
        # Mock to validate fake token
        not_expired_admin_token = FakeTokenData(timezone.now() + timedelta(minutes=5),
                                                [{'name': 'admin'}, {'name': '_member_'}])
        mock_get_keystone_admin_auth.return_value.tokens.validate.return_value = not_expired_admin_token

        cm = CrystalMiddleware()

        request = self.factory.get('/filters')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = cm.process_request(request)
        mock_get_keystone_admin_auth.assert_called()
        self.assertEqual(response, None)

        # Now token is saved in valid_tokens
        mock_get_keystone_admin_auth.reset_mock()
        request = self.factory.get('/filters')
        request.META['HTTP_X_AUTH_TOKEN'] = 'fake_token'
        response = cm.process_request(request)
        mock_get_keystone_admin_auth.assert_not_called()
        self.assertEqual(response, None)


    #
    # Aux methods
    #

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

    def configure_usernames_and_passwords_for_nodes(self):
        self.r.hmset('proxy_node:controller', {'ssh_username': 'user1', 'ssh_password': 's3cr3t', 'ssh_access': 'True'})
        self.r.hmset('object_node:storagenode1', {'ssh_username': 'user1', 'ssh_password': 's3cr3t', 'ssh_access': 'True'})
        self.r.hmset('object_node:storagenode2', {'ssh_username': 'user1', 'ssh_password': 's3cr3t', 'ssh_access': 'True'})

    def create_startup_fixtures(self):
        self.r.hmset('workload_metric:1', {'metric_name': 'm1.py', 'class_name': 'Metric1', 'execution_server': 'proxy', 'out_flow': 'False',
                                           'in_flow': 'False', 'status': 'Running', 'id': '1'})
        self.r.hmset('workload_metric:2', {'metric_name': 'm2.py', 'class_name': 'Metric2', 'execution_server': 'proxy', 'out_flow': 'False',
                                           'in_flow': 'False', 'status': 'Running', 'id': '2'})
        self.r.hmset('metric:metric1', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('metric:metric2', {'network_location': '?', 'type': 'integer'})
        self.r.hmset('policy:1',
                     {'status': 'Alive', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET compression'})
        self.r.hmset('policy:2',
                     {'status': 'Alive', 'policy_description': 'FOR TENANT:0123456789abcdef DO SET encryption'})


class FakeTokenData:
    def __init__(self, expires, roles):
        self.expires = expires
        self.roles = roles

    def __getitem__(self, i):
        if i == 'roles':
            return self.roles


class FakeTenantData:
    def __init__(self, id, name):
        self.id = id
        self.name = name
