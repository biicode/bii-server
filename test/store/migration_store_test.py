from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.store.migration_store import MigrationStore
from biicode.common.migrations.migration import Migration
import time


class MigrationStoreTest(TestWithMongo):

    def setUp(self):
        self.store = MigrationStore(self.conn,  self.__class__.__name__)

    def test_create_and_read_migration(self):
        mig = Migration()
        mig.ID = "3_my_migration"
        mig.applied_timestamp = time.time()
        self.store.store_executed_migration(mig)

        last = self.store.read_last_migrated()
        self.assertEqual(last, mig)

        mig2 = Migration()
        mig2.ID = "2_my_migration"
        mig2.applied_timestamp = time.time()
        time.sleep(0.05)
        self.store.store_executed_migration(mig2)

        # Its last yet
        last = self.store.read_last_migrated()
        self.assertEqual(last, mig2)

        mig3 = Migration()
        mig3.ID = "4_my_migration"
        mig3.applied_timestamp = time.time()
        time.sleep(0.05)
        self.store.store_executed_migration(mig3)

        last = self.store.read_last_migrated()
        self.assertEqual(last, mig3)

        applied = self.store.applied_migrations()

        self.assertEqual(len(applied), 3)
        self.assertEqual(set(applied), set([mig, mig2, mig3]))
