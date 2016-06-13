from django.test import TestCase, RequestFactory

from .views import policy_list

class NewTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()

    def test_registry_static_policy(self):
        """..."""

        # Create an instance of a GET request.
        request = self.factory.get('/registry/static_policy')
        response = policy_list(request)

        self.assertEqual(response.status_code, 200)