from mongo_test import TestWithMongo
from biicode.server.store.mongo_server_store import MongoServerStore
from db_model_creator import ModelCreator
from biicode.server.publish.publish_service import PublishService
from biicode.server.store.generic_server_store import GenericServerStore
from mock import Mock
from biicode.common.exception import ServerInternalErrorException
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.cells import SimpleCell
from biicode.common.model.blob import Blob
from biicode.common.model.content import Content
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.symbolic.block_version_table import BlockVersionTable


def publish_pack_add(pack, block_cell_name, content_text):
    name = BlockCellName(block_cell_name)
    cell1 = SimpleCell(name)
    pack.cells.add(cell1)
    pack.contents[name.cell_name] = Content(load=Blob(content_text))  # it MUST have a content to be deleted
    return cell1


class PublishTransactionTest(TestWithMongo):
    _multiprocess_shared_ = True

    def setUp(self):
        self.conn.drop_database(self._testMethodName)
        self.store = MongoServerStore(self.conn, self._testMethodName)
        self.mother = ModelCreator(self.store)
        self.user = self.mother.make_test_user()
        self.p = PublishService(self.store, self.user.ID)
        self.brl = BRLBlock('%s/%s/block/master' % (self.user.ID, self.user.ID))

        pack = PublishRequest(BlockVersion(self.brl, -1))
        pack.cells.append(SimpleCell('%s/block/r1.h' % self.user.ID))
        pack.cells.append(SimpleCell('%s/block/r2.h' % self.user.ID))
        pack.cells.append(SimpleCell('%s/block/r3.h' % self.user.ID))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('r1'))
        pack.contents['r2.h'] = Content(id_=None, load=Blob('r2'))
        pack.contents['r3.h'] = Content(id_=None, load=Blob('r3'))
        pack.deptable = BlockVersionTable()
        self.pack = pack

        self.cell_collection = self.store.db[GenericServerStore.PUBLISHED_CELL_ST]
        self.content_collection = self.store.db[GenericServerStore.PUBLISHED_CONTENT_ST]
        self.block_collection = self.store.db[GenericServerStore.BLOCK_ST]

    def tearDown(self):
        print 'tearDown %s' % self._testMethodName
        self.conn.drop_database(self._testMethodName)

    def test_publish_success(self):
        self.p.publish(self.pack)

        blocks = list(self.block_collection.find())
        cells = list(self.cell_collection.find())
        contents = list(self.content_collection.find())
        self.assertEqual(3, len(contents))
        self.assertEqual(3, len(cells))
        self.assertEquals(1, len(blocks))

        self.assertNotransactionPending()

    def test_roll_back(self):
        self.p._write_resources_to_db = Mock(side_effect=Exception('Branches update failed'))
        cells_no = len(list(self.cell_collection.find()))
        contents_no = len(list(self.content_collection.find()))
        #blocks_no = len(list(self.block_collection.find()))

        #old_block = self.store.read_block(self.brl)
        with self.assertRaises(ServerInternalErrorException):
            self.p.publish(self.pack)

        # TODO: Test that block creation is rolled back, now it isnt
        # new_block = self.store.read_block(self.brl)

        #self.assertEqual(old_block, new_block)

        cells = list(self.cell_collection.find())
        contents = list(self.content_collection.find())
        #blocks = list(self.block_collection.find())
        self.assertEqual(cells_no, len(cells))
        self.assertEqual(contents_no, len(contents))
        #self.assertEqual(blocks_no, len(blocks))

        self.assertNotransactionPending()

    def assertNotransactionPending(self):
        dbcol = self.store.db[self.store.BLOCK_TRANSACTIONS]
        transaction = dbcol.find_one({'_id': str(self.brl)})
        self.assertTrue(transaction is None)
