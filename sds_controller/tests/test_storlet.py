"""
Author: Raul Casanova Marques <raul.casanova@estudiants.urv.cat>
"""
import requests
import json
import unittest


storlet_url = 'http://localhost:18000/filters/'
auth_token = 'f07c1ad8d8864c6e842a6e01a9573dd3'
headers_param = {'X-Auth-Token':auth_token, 'Content-Type':"application/json"}


class Test_Storlet(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.storlet_data_correct = {'name':'test.jar', 'language':'java', 'interface_version':1.0, 'dependencies':' ', 'object_metadata':'no', 'main':'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True, 'has_reverse': True, 'execution_server_default':'localhost', 'execution_server_reverse':'localhost'}
        self.storlet_data_wrong_id = {'id':1, 'name':'test.jar', 'language':'java', 'interface_version':1.0, 'dependencies':' ', 'object_metadata':'no', 'main':'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True, 'has_reverse': True, 'execution_server_default':'localhost', 'execution_server_reverse':'localhost'}
        self.storlet_data_wrong_path = {'name':'test.jar', 'language':'java', 'interface_version':1.0, 'dependencies':' ', 'object_metadata':'no', 'main':'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True, 'has_reverse': True, 'execution_server_default':'localhost', 'execution_server_reverse':'localhost', 'path':'/'}
        self.storlet_data_all = {'id': 1, 'name':'test.jar', 'language':'java', 'interface_version':1.0, 'dependencies':' ', 'object_metadata':'no', 'main':'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True, 'has_reverse': True, 'execution_server_default':'localhost', 'execution_server_reverse':'localhost', 'path':'/'}

        self.storlet_keys = ('id', 'name', 'language', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_put', 'is_get', 'has_reverse', 'execution_server_default', 'execution_server_reverse', 'path')


    """ PUT """
    def test_put_without_parameters(self):
        # PUT request without parameters
        req = requests.put(storlet_url, headers=headers_param)
        self.assertEquals(req.status_code, 405)

    def test_put_with_parameters(self):
        # PUT request with parameters
        req = requests.put(storlet_url, self.storlet_data_correct, headers=headers_param)
        self.assertEquals(req.status_code, 405)


    """ POST """
    def test_post_without_parameters(self):
        # POST request without parameters
        req = requests.post(storlet_url, headers=headers_param)
        self.assertEquals(req.status_code, 400)



if __name__ == "__main__":
    unittest.main()