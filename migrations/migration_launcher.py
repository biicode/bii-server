from biicode.server.conf import BII_MONGO_URI, BII_MAX_MONGO_POOL_SIZE
from biicode.common.migrations.migration_manager import MigrationManager
from biicode.server.store.migration_store import MigrationStore
from biicode.server.store.mongo_server_store import MongoServerStore
import time
from pymongo.mongo_client import MongoClient
from biicode.server.migrations.migrations import SERVER_MIGRATIONS
from biicode.common.output_stream import OutputStream


def launch():
    # Default MongoClient params are:
    # w=1  perform a write acknowledgement only in primary
    # j=False the driver does not add j to the getlasterror command
    # fsync=False the server does not add Sync to disk. to the getlasterror command
    mongo_connection = MongoClient(BII_MONGO_URI, max_pool_size=BII_MAX_MONGO_POOL_SIZE)
    migration_store = MigrationStore(mongo_connection)
    server_store = MongoServerStore(mongo_connection)
    biiout = OutputStream()
    manager = MigrationManager(migration_store, SERVER_MIGRATIONS, biiout)

    # Pass in kwargs all variables migrations can need
    n1 = time.time()
    manager.migrate(server_store=server_store)
    n2 = time.time()
    biiout.info('All took %s seconds' % str(n2 - n1))

    # DO NOT REMOVE THIS PRINT NOR REPLACE WITH LOGGER, ITS A CONSOLE SCRIPT
    # INVOKED IN DEPLOYMENT PROCESS AND ITS NECESSARY IT PRINTS TO OUTPUT
    print biiout


if __name__ == "__main__":
    launch()
