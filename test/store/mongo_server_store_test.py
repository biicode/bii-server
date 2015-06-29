from nose.core import run
from mongo_test import TestWithMongo
from biicode.server.exception import (BiiPendingTransactionException,
                                      MongoNotCurrentObjectException, MongoStoreException,
                                      MongoNotFoundUpdatingException)
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.model.block import Block
from biicode.common.model.brl.brl_block import BRLBlock
from db_model_creator import ModelCreator
from biicode.common.test import model_creator
from biicode.common.utils.bii_logging import logger
import mock
from biicode.server.utils import update_if_current
from biicode.server.utils.update_if_current import safe_retry
from biicode.server.store.mongo_store import MongoStore
from biicode.server.test.store.mongo_test import MONGODB_TEST_PORT
from biicode.common.model.renames import Renames
from biicode.server.store.generic_server_store import GenericServerStore
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.common.exception import AlreadyInStoreException
from biicode.common.model.id import ID
from biicode.common.model.brl.block_cell_name import BlockCellName


class MongoStoreTest(TestWithMongo):
    _multiprocess_shared_ = True

    def setUp(self):
        self.store = MongoServerStore(self.conn, self.__class__.__name__)
        self.mother = ModelCreator(self.store)
        self.user = self.mother.make_test_user()

    def test_two_connections_sharing_data(self):
        connection2 = MongoStore.makeConnection('localhost', MONGODB_TEST_PORT)
        store2 = MongoServerStore(connection2, self.__class__.__name__)
        user = self.mother.make_test_user()

        user2 = store2.read_user(user.ID)
        self.assertEqual(user.ID, user2.ID)

    def test_dupe_user_name(self):
        with self.assertRaises(AlreadyInStoreException):
            self.store.create_user(self.user)

    def test_insert_read_block(self):
        name = BRLBlock('%s/%s/TestBlock/trunk' % (self.user.ID, self.user.ID))
        mid = self.user.add_block(name)
        block = Block(mid, name)
        self.store.create_block(block)
        retrieved1 = self.store.read_block(name)
        self.assertEqual(block, retrieved1)

    def test_insert_read_published_resource(self):
        block = self.mother.make_block()
        resource = model_creator.make_published_resource(block, 'TestUser/geom/sphere.cpp')
        self.store.create_published_cells([resource])
        retrieved = self.store.read_published_cells([resource.ID])
        self.assertEqual(resource, retrieved[resource.ID])
        self.assertEqual(1, len(retrieved))

    def test_insert_read_published_content(self):
        block = self.mother.make_block(self.user)
        brl = BlockCellName('%s/geom/sphere.cpp' % block.ID.owner)
        content = model_creator.make_content(brl, False)
        content.ID = ID((2, 3, 4))  # 'dummy_id'
        self.store.create_published_contents([content])
        retrieved = self.store.read_published_contents([content.ID])
        self.assertEqual(content, retrieved[content.ID])
        self.assertEqual(1, len(retrieved))

    def test_two_publish_transactions(self):
        brl = BRLBlock('user/user/block/master')
        self.store.requestBlockTransaction(brl)
        with self.assertRaises(BiiPendingTransactionException):
            self.store.requestBlockTransaction(brl)

    def test_dirty_object(self):
        u1 = self.mother.make_test_user()

        u_ = self.store.read_user(u1.ID)
        u1_bis = self.store.read_user(u1.ID)

        self.store.update_user(u_)  # Now b1_bis is dirty!! is not updated from database
        self.assertRaises(MongoNotCurrentObjectException, self.store.update_user, u1_bis)

    def test_txn_multiple_updates_same_object(self):
        for _ in range(10):
            # Not dirty!! same memory object with up to date counter
            self.store.update_user(self.user)

    def test_txn_limit_counter(self):
        bclean = self.store.read_user(self.user.ID)
        bdirty = self.store.read_user(self.user.ID)

        self.store.update_user(bclean)
        # dirty!! same memory object with up to date counter
        self.assertRaises(MongoNotCurrentObjectException, self.store.update_user, bdirty)

    def test_txn_limit_counter_overflow(self):
        b1 = self.user
        update_if_current.TXN_MAX_C = 10

        logger.debug("CONTADOR MAXIMO:" + str(update_if_current.TXN_MAX_C))
        bclean = self.store.read_user(b1.ID)
        bdirty = self.store.read_user(b1.ID)

        for _ in range(update_if_current.TXN_MAX_C):
            # 10 updates in transaction (increments tx counter each)
            self.store.update_user(bclean)

        self.store.update_user(bdirty)  # dirty but cheated!! counter overflowed

    def testTxnDecorator(self):
        # Call this method, it will execute the code until not MongoDirtyObjectException raises
        m = mock.Mock(return_value="ok, mock called")
        self.i = 0
        ret = self._transaction_method(m, 5, max_uncouple_ms=50, max_iterations=10)
        self.assertEqual(ret, "OK!!!")
        m.assert_called_with(4)
        self.i = 0
        ret = self._transaction_method(m, 9, max_uncouple_ms=100, max_iterations=10)
        self.assertEqual(ret, "OK!!!")
        m.assert_called_with(8)
        self.i = 0
        self.assertRaises(MongoStoreException, self._transaction_method, m, 30, max_uncouple_ms=10,
                          max_iterations=30)

    @safe_retry
    def _transaction_method(self, mock_obj, n_times):
        ''' raises dirty object exception only N times '''
        if self.i < n_times:
            mock_obj(self.i)
            self.i = self.i + 1
            raise MongoNotCurrentObjectException("Oh!! an exception again...")
        return "OK!!!"

    def testUpdateNotExistingError(self):
        # Not existing collection with not existing object
        self.assertRaises(MongoNotFoundUpdatingException, self.store._update_collection,
                          "notexitingcollection", {'a': 1}, set_statement={'a': 2},
                           upsert=False, trx_record=False)

        # Existing collection with not existing object
        self.assertRaises(MongoNotFoundUpdatingException, self.store._update_collection,
                          GenericServerStore.USER_ST, {'a': 1}, set_statement={'a': 2},
                           upsert=False, trx_record=False)

        # Existing object update
        myblock = Block(ID((9, 2)), BRLBlock("user/user/myblock/master"))
        self.store.create_block(myblock)
        ret = self.store._update_collection(GenericServerStore.BLOCK_ST,
                                            {Block.SERIAL_ID_KEY: myblock.ID.serialize()},
                                            set_statement={"$set":
                                                           {Block.SERIAL_CONTENT_COUNTER: 89}},
                                            upsert=False, trx_record=False)
        self.assertIsInstance(ret, dict)

        # Existing object update but without changes
        ret = self.store._update_collection(GenericServerStore.BLOCK_ST,
                                            {Block.SERIAL_ID_KEY: myblock.ID.serialize()},
                                            set_statement={"$set":
                                                           {Block.SERIAL_CONTENT_COUNTER: 89}},
                                            upsert=False, trx_record=False)
        self.assertIsInstance(ret, dict)

        # Upsert an existing object
        the_id = ID((22, 33))
        myblock = Block(the_id, BRLBlock("user/user/myblock2/master"))
        self.store.create_block(myblock)
        ret = self.store._update_collection(GenericServerStore.BLOCK_ST,
                                            {Block.SERIAL_ID_KEY: myblock.ID.serialize()},
                                            set_statement={"$set":
                                                           {Block.SERIAL_CONTENT_COUNTER: 89}},
                                            upsert=True, trx_record=False)
        self.assertIsInstance(ret, dict)

    def test_update_permissions(self):
        myblock = self.mother.make_block(self.user)
        # Check default permissions
        access = self.store.read_block_permissions(myblock.ID)
        perm = ElementPermissions(False)
        self.assertTrue(access, perm)
        # Update permissions
        access.read.grant("pepe")
        access.read.grant("jaunito")
        access.write.grant("jaunito")
        self.store.update_block_permissions(access)

        perms = self.store.read_block_permissions(myblock.ID)

        self.assertTrue(perms.read.is_granted("pepe"))
        self.assertFalse(perms.write.is_granted("pepe"))

        self.assertTrue(perms.read.is_granted("jaunito"))
        self.assertTrue(perms.write.is_granted("jaunito"))

if __name__ == "__main__":
    run()
