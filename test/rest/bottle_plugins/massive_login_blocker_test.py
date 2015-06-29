import unittest
from biicode.server.rest.bottle_plugins.massive_error_blocker_bottle_plugin import MassiveErrorBlockerBottlePlugin
from bottle import HTTPResponse, request
from datetime import timedelta
from mock import Mock
import time
from biicode.test.fake_mem_store import FakeMemStore


class MassiveErrorBlockerTest(unittest.TestCase):
    """
    """

    def setUp(self):
        self.ip = "84.34.13.122"
        self.login_ok = True
        self.memory = FakeMemStore()
        self.callback = Mock(wraps=self._callback)
        request.environ['REMOTE_ADDR'] = self.ip

    def tearDown(self):
        pass

    def testOtherExceptionIsRaised(self):
        '''if its not a auth problem, we raise it'''
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=100,
                                                      bantime=timedelta(seconds=0.2))
        self.assertRaises(KeyError, self.plugin.apply(self._callback_raiser, None))

    def testCallbackCalled(self):
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=100,
                                                      bantime=timedelta(seconds=0.2))
        self.plugin.apply(self.callback, None)()
        self.callback.assert_any_call()
        self.assertEquals(len(self.memory.memory), 0)

    def testMaxMinusOneAttemptsAllowed(self):
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.2))
        self.login_ok = False
        for i in xrange(9):  # 0 to 8 failures
            self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        self.login_ok = True
        self.plugin.apply(self.callback, None)("hello2")
        self.callback.assert_called_with("hello2")  # If called, its not blocked

    def testMaxAttemptsBlocked(self):
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.2))
        self.login_ok = False
        for i in xrange(10):  # 0 to 9 failures
            self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        self.login_ok = True
        self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello2")  # Blocked
        try:
            self.plugin.apply(self.callback, None)("hello2")
        except HTTPResponse, e:
            self.assertIn("Banned", e.body)

    def testCounterExpired(self):
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.2))
        self.login_ok = False
        for i in xrange(9):  # 0 to 8 failures, 1 more left to ban
            self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
            self.assertEqual(i + 1, self.plugin.ip_count(self.ip))
            self.callback.assert_called_with("hello")

        # Wait delta time and make another fail
        time.sleep(0.11)
        self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
        self.assertEqual(1, self.plugin.ip_count(self.ip))

        self.login_ok = True
        self.plugin.apply(self.callback, None)("hello2")
        self.assertEquals(len(self.memory.memory), 0)

    def testBanExpired(self):
        self.plugin = MassiveErrorBlockerBottlePlugin(self.memory,
                                                      delta=timedelta(seconds=0.1),
                                                      max_events=10,
                                                      bantime=timedelta(seconds=0.2))
        self.login_ok = False
        for i in xrange(13):  # 0 to 12 failures, banned
            self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")

        # Wait delta time and make another fail, check keep banned
        time.sleep(0.1)
        self.login_ok = True
        self.assertRaises(HTTPResponse, self.plugin.apply(self.callback, None), "hello")
        try:
            self.plugin.apply(self.callback, None)("hello2")
        except HTTPResponse, e:
            self.assertIn("Banned", e.body)

        # Wait to bantime and check again
        time.sleep(0.11)  # 0.1 + 0.1 >= Bantime
        self.plugin.apply(self.callback, None)("hello2")
        self.assertEquals(len(self.memory.memory), 0)

    def _callback(self, *args, **kwargs):
        if not self.login_ok:
            raise HTTPResponse("'Banned'",
                               "401 Unauthorized",
                               {"WWW-Authenticate": 'Basic realm="Login Required"'})
        return HTTPResponse("OK", "200 OK", {})

    def _callback_raiser(self, *args, **kwargs):
        raise KeyError()
