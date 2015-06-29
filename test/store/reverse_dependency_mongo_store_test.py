from nose.core import run
from mongo_test import TestWithMongo
from biicode.server.model.reverse_dependency import ReverseDependency
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.store.reverse_dependency_mongo_store import ReverseDependencyMongoStore
from biicode.common.model.symbolic.block_version import BlockVersion


class ReverseDependencyMongoStoreTest(TestWithMongo):

    def setUp(self):
        self.store = MongoServerStore(self.conn, self.__class__.__name__)
        self.store = ReverseDependencyMongoStore(self.store)
        bver = BlockVersion.loads("creator/block(owner/branch):2")
        self.bv2 = BlockVersion.loads("creator2/block(owner2/branch):2")
        self.bv3 = BlockVersion.loads("creator3/block(owner3/branch):3")

        self.reverse = ReverseDependency(bver)
        self.reverse.add_dependant_version(self.bv2)
        self.reverse.add_dependant_version(self.bv3)

        self.store.upsert_reverse_dependencies(self.reverse)

        # Other version of same block
        bver2 = BlockVersion.loads("creator/block(owner/branch):3")
        self.reverse2 = ReverseDependency(bver2)
        self.reverse2.add_dependant_version(self.bv2)
        self.reverse2.add_dependant_version(self.bv3)

        self.store.upsert_reverse_dependencies(self.reverse2)

    def test_read_and_upsert_reverse_dependencies(self):

        reverse_readed = self.store.read_direct_reverse_dependencies(self.reverse.version)

        self.assertEquals(self.reverse, reverse_readed)

        # Now add directly to mongo a new dependency
        new_ver = BlockVersion.loads("creator3/block3(owner3/branch3):3")
        self.store.add_reverse_dependency_to(self.reverse.version, new_ver)

        reverse_readed = self.store.read_direct_reverse_dependencies(self.reverse.version)

        self.reverse.add_dependant_version(new_ver)
        self.assertEquals(self.reverse, reverse_readed)


if __name__ == "__main__":
    run()
