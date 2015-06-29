import unittest
from bottle import HTTPResponse, request
from datetime import timedelta
from mock import Mock
from biicode.server.rest.bottle_plugins.dos_blocker_bottle_plugin import DOSBlockerBottlePlugin
import time
from biicode.test.fake_mem_store import FakeMemStore
from biicode.common.utils.bii_logging import logger


class DOSBlockerTest(unittest.TestCase):
    """
    """

    def setUp(self):
        self.ip = "84.34.13.122"
        self.memory = FakeMemStore()
        self.callback = Mock(wraps=self._callback)
        self.bancallback = Mock(wraps=self._ban_callback)
        request.environ['REMOTE_ADDR'] = self.ip
        self.fake_response = HTTPResponse("'Seven horses come from Bonanza...'",
                            "401 Unauthorized",
                            {"WWW-Authenticate": 'Basic realm="Login Required"'})

    def tearDown(self):
        pass

    def testCallbackCalled(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                             delta=timedelta(seconds=0.1),
                                             max_events=10,
                                             bantime=timedelta(seconds=60),
                                             callback_ip_banned=self.bancallback)
        self.plugin.apply(self.callback, None)()
        self.callback.assert_any_call()
        self.assertEqual(1, self.plugin.ip_count(self.ip))

    def testMaxMinusOneAttemptsAllowed(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                             delta=timedelta(seconds=0.5),
                                             max_events=10,
                                             bantime=timedelta(seconds=0.2),
                                             callback_ip_banned=self.bancallback)
        for i in xrange(9):  # 0 to 8 failures
            self.plugin.apply(self.callback, None)("hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        self.plugin.apply(self.callback, None)("hello2")
        self.callback.assert_called_with("hello2")  # If called, its not blocked

    def testMaxAttemptsBlocked(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                             delta=timedelta(seconds=0.1),
                                             max_events=10,
                                             bantime=timedelta(seconds=0.2),
                                             banned_http_response=self.fake_response,
                                             callback_ip_banned=self.bancallback
                                             )
        for i in xrange(10):  # 0 to 9 failures
            self.plugin.apply(self.callback, None)("hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello2")  # Blocked
        try:
            self.plugin.apply(self.callback, None)("hello2")
        except HTTPResponse, e:
            self.assertIn("Bonanza", e.body)

    def testCounterExpired(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                             delta=timedelta(seconds=0.1),
                                             max_events=10,
                                             bantime=timedelta(seconds=0.2),
                                             banned_http_response=self.fake_response,
                                             callback_ip_banned=self.bancallback)
        for i in xrange(9):  # 0 to 8 failures, 1 more left to ban
            self.plugin.apply(self.callback, None)("hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        #Wait delta time and make another request
        time.sleep(0.11)
        self.plugin.apply(self.callback, None)("hello2")
        self.assertEquals(len(self.memory.memory), 1)

    def testBanExpired(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.4),
                                                      callback_ip_banned=self.bancallback)
        for i in xrange(13):  # 0 to 12 failures, banned
            if i > 9:
                self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
            else:
                self.plugin.apply(self.callback, None)("hello")

        #Wait delta time and make another fail, check keep banned
        time.sleep(0.2)
        self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")

        #Wait to bantime and check again
        time.sleep(0.21)  # 0.2 + 0.2 >= Bantime
        self.plugin.apply(self.callback, None)("hello2")

    def testCallBackBannedCalled(self):
        self.plugin = DOSBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.4),
                                                      callback_ip_banned=self.bancallback)
        for i in xrange(20):  # 0 to 12 failures, banned
            if i > 9:
                self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
            else:
                self.plugin.apply(self.callback, None)("hello")
            if i > 11:
                self.assertEqual(self.bancallback.call_count, 1)  # Only one callback

    def _callback(self, *args, **kwargs):
        pass

    def _ban_callback(self, ip, counter, time):
        logger.debug("BAN CALLBACK!! " + ip + " COUNT:" + str(counter) + " IN: " + str(time))
