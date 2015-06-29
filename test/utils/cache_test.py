import unittest
from datetime import timedelta
from biicode.server.utils.cache import MemCachedCollection
from biicode.test.fake_mem_store import FakeMemStore
from mock import Mock


class Test(unittest.TestCase):
    def setUp(self):
        self.mem = FakeMemStore()
        self.cache = MemCachedCollection(self.mem, "animals")

    def test_write_cache(self):
        self.cache.set("timon", "pumba", 2)
        self.assertEqual(self.cache.get("timon"), "pumba")

    def test_delete_cache(self):
        self.cache.set("timon", "pumba")
        self.cache.delete("timon")
        self.assertEqual(self.cache.get("timon"), None)

    def test_get_inexistent_element(self):
        self.assertEqual(self.cache.get("timon"), None)

    def test_parameters_ok(self):
        self.mem.set = Mock()
        self.cache.set("timon", "pumba", 1.2)
        self.mem.set.assert_called_once_with("animals@timon", "pumba", time=1)

        self.mem.set = Mock()
        self.cache.set("timon2", "pumba2")
        self.mem.set.assert_called_once_with("animals@timon2", "pumba2", time=0)
