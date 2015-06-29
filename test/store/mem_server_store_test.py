from biicode.server.model.block import Block
from biicode.common.model.id import ID
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.cells import SimpleCell
from biicode.common.model.content import Content
from biicode.common.model.blob import Blob
import datetime
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.test.testing_mem_server_store import TestingMemServerStore
from biicode.server.test.store.mongo_test import TestWithMongo
from nose_parameterized.parameterized import parameterized
from biicode.server.store.mongo_server_store import MongoServerStore


class MemServerStoreTest(TestWithMongo):

    @parameterized.expand([(MongoServerStore, ), (TestingMemServerStore, )])
    def test_read_published_blocks_info(self, store_cls):
        """Insert a block and read all published blocks info (brl, lastpubdate)"""
        if store_cls == MongoServerStore:
            store = MongoServerStore(self.conn, self.__class__.__name__)
        else:
            store = TestingMemServerStore()
        block = Block(ID((23, 23)), BRLBlock("bonjovi/bonjovi/itsmylife/master"))
        ppack = PublishRequest(block.last_version())
        r1 = SimpleCell('user/block/r1.h')
        ppack.cells.append(r1)
        ppack.contents['r1.h'] = Content(id_=None, load=Blob('hola'))

        block.add_publication(ppack)
        store.create_block(block, False)
        ret = store.read_published_blocks_info()
        first = ret.next()

        self.assertEquals(first[0], "bonjovi/bonjovi/itsmylife/master")
        self.assertEquals(first[1].__class__, datetime.datetime)
