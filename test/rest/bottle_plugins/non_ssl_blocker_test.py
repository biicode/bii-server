import unittest
from bottle import HTTPResponse, request
from mock import Mock
from biicode.server.rest.bottle_plugins.non_ssl_blocker_bottle_plugin import NonSSLBlockerBottlePlugin


class NonSSLBlocker(unittest.TestCase):
    """
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testHttpsOK(self):
        self.plugin = NonSSLBlockerBottlePlugin()
        request.headers.get = Mock(return_value='https')
        self.plugin.apply(self._callback, None)()

    def testHttpsERROR(self):
        self.plugin = NonSSLBlockerBottlePlugin()
        request.headers.get = Mock(return_value='http')
        self.assertRaises(HTTPResponse, self.plugin.apply(self._callback, None))

    def _callback(self, *args, **kwargs):
        return True
