import requests
from allianceauth.utils.testing import NoSocketsTestCase, SocketAccessError


class TestNoSocketsTestCase(NoSocketsTestCase):
    def test_raises_exception_on_attempted_network_access(self):

        with self.assertRaises(SocketAccessError):
            requests.get("https://www.google.com")
