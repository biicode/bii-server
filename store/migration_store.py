from biicode.server.store.mongo_store import MongoStore
from biicode.common.migrations.migration import Migration
import pymongo


class MigrationStore(MongoStore):

    collection = "migration"

    def __init__(self, connection, databasename=None):
        MongoStore.__init__(self, connection, databasename)

    def applied_migrations(self):
        dbcol = self.db[MigrationStore.collection]
        doc = dbcol.find().sort([(Migration.SERIAL_TIMESTAMP_KEY, pymongo.DESCENDING)])
        mig = [Migration.deserialize(mig) for mig in doc]
        mig.sort()
        return mig

    def read_last_migrated(self):

        dbcol = self.db[MigrationStore.collection]
        doc = dbcol.find().sort([(Migration.SERIAL_TIMESTAMP_KEY, pymongo.DESCENDING)])

        if not doc or doc.count() == 0:
            return None
        else:
            return Migration.deserialize(doc[0])

    def store_executed_migration(self, migration):
        return self.create(migration, MigrationStore.collection)
