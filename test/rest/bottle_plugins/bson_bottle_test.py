import unittest
from mock import Mock
from biicode.common.utils.bii_logging import logger
from biicode.server.rest.bottle_plugins.bson_bottle_plugin import BSONBottlePlugin,\
    BSONBottlePluginException
import bottle
from bson import BSON
from bottle import request, HTTPResponse, PluginError
from biicode.server.conf import BII_MAX_MEMORY_PER_REQUEST


class BsonBottleTest(unittest.TestCase):
    """Bottle plugin for automatic parse a BSON request and pass a  """

    def setUp(self):
        self.plugin = BSONBottlePlugin()
        self.ip = "84.34.13.122"
        self.callback = Mock(wraps=self._callback)
        self.callbacknobson = Mock(wraps=self._callbackno)
        bottle.request.environ['REMOTE_ADDR'] = self.ip
        bottle.request.environ['CONTENT_TYPE'] = 'application/bson'
        self.context = Mock()
        self.context.callback = self._callback

        self.contextnobson = Mock(wraps=self._callbackno)
        self.contextnobson.callback = self._callbackno

        self.__set_bson_content({"therivermen": "ehhhhhmacarena"})

    def tearDown(self):
        pass

    def testAddOtherPluginWithSameKeywork(self):
        app = Mock()
        bad_plugin = Mock()
        bad_plugin.keyword = "bson_data"
        app.plugins = set([bad_plugin])
        self.assertRaises(PluginError, self.plugin.setup, app)

    def testCallbackCalled(self):
        self.plugin.apply(self.callback, self.context)()
        self.assertTrue(self.callback.called)

    def testNotBsonRequest(self):
        bottle.request.environ['CONTENT_TYPE'] = 'mouse/mikey'
        self.assertRaises(BSONBottlePluginException, self.plugin.apply(self.callback, self.context))

    def testNotBsonRequestWithNoBonDataParameter(self):
        bottle.request.environ['CONTENT_TYPE'] = 'mouse/mikey'
        # If there is not bson_data parameter callback will be called correctly and without bson_data parameter
        self.plugin.apply(self.callbacknobson, self.contextnobson)()
        self.callbacknobson.assert_called_once_with()

    def testNoContent(self):
        bottle.request.environ["CONTENT_LENGTH"] = 0
        self.assertRaises(BSONBottlePluginException,
                          self.plugin.apply(self.callback, self.context))

    def testMaxContent(self):
        bottle.request.environ["CONTENT_LENGTH"] = (BII_MAX_MEMORY_PER_REQUEST) + 1
        self.assertRaises(BSONBottlePluginException,
                          self.plugin.apply(self.callback, self.context))

    def testAbortWithBSON(self):
        tmp = self.plugin.abort_with_bson(401, {"kk": 2})
        self.assertIsInstance(tmp, HTTPResponse)
        self.assertEquals("application/bson", tmp.content_type)
        self.assertEquals(401, tmp.status_code)
        self.assertEquals(str(BSON.encode({"kk": 2})), tmp.body)

    def _callback(self, bson_data=""):
        logger.debug("Bson: " + str(bson_data))
        pass

    def _callbackno(self):
        pass

    def __set_bson_content(self, data):
        bottle.request.environ['wsgi.input'] = str(BSON.encode(data))
        bottle.request.environ["CONTENT_LENGTH"] = len(bottle.request.environ['wsgi.input'])
        bottle.request.body = Mock
        bottle.request.body.read = Mock(return_value=bottle.request.environ['wsgi.input'])
