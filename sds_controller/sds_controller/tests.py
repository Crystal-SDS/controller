import redis

from django.conf import settings
from django.core.urlresolvers import resolve
from django.test import TestCase, override_settings

from .common_utils import get_all_registered_nodes, remove_extra_whitespaces, to_json_bools

# Tests use database=10 instead of 0.
@override_settings(REDIS_CON_POOL=redis.ConnectionPool(host='localhost', port=6379, db=10))
class MainTestCase(TestCase):
    def setUp(self):
        self.r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)
        self.create_nodes()

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
        bdict = {'a':'True', 'b':'False', 'c':'True', 'd':'False'}
        to_json_bools(bdict, 'a', 'b', 'c')
        self.assertEqual(bdict['a'], True)
        self.assertNotEqual(bdict['a'], 'True')
        self.assertEqual(bdict['b'], False)
        self.assertNotEqual(bdict['b'], 'False')
        self.assertEqual(bdict['c'], True)
        self.assertNotEqual(bdict['c'], 'True')
        self.assertEqual(bdict['d'], 'False')
        self.assertNotEqual(bdict['d'], False)

    #
    # URL tests
    #

    def test_urls(self):
        resolver = resolve('/filters/')
        self.assertEqual(resolver.view_name, 'storlet.views.storlet_list')

        resolver = resolve('/filters/123')
        self.assertEqual(resolver.view_name, 'storlet.views.storlet_detail')
        self.assertEqual(resolver.kwargs, {'storlet_id': '123'})

        resolver = resolve('/filters/123/data')
        self.assertEqual(resolver.view_name, 'storlet.views.StorletData')
        self.assertEqual(resolver.kwargs, {'storlet_id': '123'})

        resolver = resolve('/registry/nodes/')
        self.assertEqual(resolver.view_name, 'registry.views.node_list')

        resolver = resolve('/registry/nodes/node1')
        self.assertEqual(resolver.view_name, 'registry.views.node_detail')
        self.assertEqual(resolver.kwargs, {'node_id': 'node1'})

    #
    # Aux methods
    #

    def create_nodes(self):
        self.r.hmset('node:controller',
                     {'ip': '192.168.2.1', 'last_ping': '1467623304.332646', 'type': 'proxy', 'name': 'controller',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('node:storagenode1',
                     {'ip': '192.168.2.2', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode1',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
        self.r.hmset('node:storagenode2',
                     {'ip': '192.168.2.3', 'last_ping': '1467623304.332646', 'type': 'object', 'name': 'storagenode2',
                      'devices': '{"sdb1": {"free": 16832876544, "size": 16832880640}}'})
