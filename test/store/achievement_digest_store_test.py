import unittest
from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.store.achievement_digest_mongo_store import AchievementDigestMongoStore,\
    AchievementDigest


class AchievementDigestStoreTest(TestWithMongo):

    def setUp(self):
        unittest.TestCase.setUp(self)
        tmp = MongoServerStore(self.conn, self.__class__.__name__)
        self.store = AchievementDigestMongoStore(tmp)

    def test_achievement_counters(self):

        self.store.increment_total_publish_counter("pepe")
        self.assert_digest(0, 1, 0, [], ["pepe"], [])

        self.store.increment_total_publish_counter("pepe2")
        self.assert_digest(0, 2, 0, [], ["pepe2", "pepe"], [])

        self.store.increment_total_read_counter("pepe2")
        self.assert_digest(1, 2, 0, ["pepe2"], ["pepe2", "pepe"], [])

        self.store.increment_total_reuse_counter("pepe3")
        self.assert_digest(1, 2, 1, ["pepe2"], ["pepe2", "pepe"], ["pepe3"])

        self.store.increment_total_reuse_counter("pepe4")
        self.assert_digest(1, 2, 2, ["pepe2"], ["pepe2", "pepe"], ["pepe4", "pepe3"])

        self.store.increment_total_reuse_counter("pepe5")
        self.assert_digest(1, 2, 3, ["pepe2"], ["pepe2", "pepe"], ["pepe5", "pepe4", "pepe3"])

    def assert_digest(self, reads, publish, reuses, list_reads, list_published, list_reuses):
        digest = self.store.read_achievement_digest()
        self.assertIsInstance(digest, AchievementDigest)
        self.assertEquals(digest.num_reads, reads)
        self.assertEquals(digest.num_publish, publish)
        self.assertEquals(digest.num_reuses, reuses)
        self.assertEquals(digest.last_reads, list_reads)
        self.assertEquals(digest.last_published, list_published)
        self.assertEquals(digest.last_reuses, list_reuses)

if __name__ == "__main__":
    unittest.main()
