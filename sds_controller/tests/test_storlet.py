from rest_framework import status
import requests
import json
import unittest


storlet_url = 'http://localhost:8000/filters/'
# TODO: Try to obtain the token automatically before start the tests. setUpClass method.
auth_token = 'f07c1ad8d8864c6e842a6e01a9573dd3'
headers_param = {'X-Auth-Token': auth_token, 'Content-Type': "application/json"}


class Test_Storlet(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)

        self.storlet_less_data = {'name': 'test.jar', 'language': 'java', 'interface_version': 1.0, 'dependencies': ' ',
                                  'object_metadata': 'no', 'main': 'com.ibm.filter.identity.Identityfilter'}

        self.storlet_data_correct = {'name': 'test.jar', 'language': 'java', 'interface_version': 1.0,
                                     'dependencies': ' ', 'object_metadata': 'no',
                                     'main': 'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True,
                                     'has_reverse': True, 'execution_server_default': 'localhost',
                                     'execution_server_reverse': 'localhost'}

        self.storlet_data_wrong_id = {'id': 1, 'name': 'test.jar', 'language': 'java', 'interface_version': 1.0,
                                      'dependencies': ' ', 'object_metadata': 'no',
                                      'main': 'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True,
                                      'has_reverse': True, 'execution_server_default': 'localhost',
                                      'execution_server_reverse': 'localhost'}

        self.storlet_data_wrong_path = {'name': 'test.jar', 'language': 'java', 'interface_version': 1.0,
                                        'dependencies': ' ', 'object_metadata': 'no',
                                        'main': 'com.ibm.filter.identity.Identityfilter', 'is_put': True,
                                        'is_get': True, 'has_reverse': True, 'execution_server_default': 'localhost',
                                        'execution_server_reverse': 'localhost', 'path': '/'}

        self.storlet_data_all = {'id': 1, 'name': 'test.jar', 'language': 'java', 'interface_version': 1.0,
                                 'dependencies': ' ', 'object_metadata': 'no',
                                 'main': 'com.ibm.filter.identity.Identityfilter', 'is_put': True, 'is_get': True,
                                 'has_reverse': True, 'execution_server_default': 'localhost',
                                 'execution_server_reverse': 'localhost', 'path': '/'}

        self.storlet_keys = ('id', 'name', 'language', 'interface_version', 'dependencies', 'object_metadata', 'main', 'is_put', 'is_get',
                             'has_reverse', 'execution_server_default', 'execution_server_reverse', 'path')

    """ Storlet List - PUT """

    def _test_storlet_list_put_without_parameters(self):
        # PUT request without parameters
        req = requests.put(storlet_url, headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def _test_storlet_list_put_with_parameters(self):
        # PUT request with parameters
        req = requests.put(storlet_url, json.dumps(self.storlet_data_correct), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    """ Storlet List - POST """

    def _test_storlet_list_post_without_parameters(self):
        # POST request without parameters
        req = requests.post(storlet_url, headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_400_BAD_REQUEST)

    def _test_storlet_list_post_with_wrong_parameters_sending_id(self):
        # POST request with wrong parameters sending id
        req = requests.post(storlet_url, json.dumps(self.storlet_data_wrong_id), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_400_BAD_REQUEST)

    def _test_storlet_list_post_with_wrong_parameters_sending_path(self):
        # POST request with wrong parameters sending path
        req = requests.post(storlet_url, json.dumps(self.storlet_data_wrong_path), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_400_BAD_REQUEST)

    def _test_storlet_list_post_with_correct_parameters(self):
        # POST request with correct parameters
        req = requests.post(storlet_url, json.dumps(self.storlet_data_correct), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_201_CREATED)

    def _test_storlet_list_post_with_less_correct_parameters(self):
        # POST request with less correct parameters
        req = requests.post(storlet_url, json.dumps(self.storlet_less_data), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_400_BAD_REQUEST)

    # if test_post_with_wrong_parameters_sending_path is ok, data not contains path, so don't check if data contains path
    def _test_storlet_list_return_post_with_correct_parameters_and_data_not_contains_path(self):
        # POST request to get return with correct parameters
        req = requests.post(storlet_url, json.dumps(self.storlet_data_correct), headers=headers_param)
        content = req.json()
        for key in self.storlet_keys[:-1]:  # Without path
            self.assertEquals(content.has_key(key), True)

    """ Storlet Detail - POST """

    def test_storlet_detail_post_without_parameters(self):
        # POST request without parameters
        req = requests.post(storlet_url + '1/', headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_storlet_detail_post_with_parameters(self):
        # POST request with parameters
        req = requests.post(storlet_url + '1/', json.dumps(self.storlet_data_correct), headers=headers_param)
        self.assertEquals(req.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


if __name__ == "__main__":
    unittest.main()
