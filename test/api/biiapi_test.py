from biicode.server.api.bii_service import BiiService
from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.test.store.db_model_creator import ModelCreator
from biicode.common.exception import NotFoundException
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.model.content import Content
from biicode.common.model.cells import SimpleCell
from biicode.common.model.version_tag import STABLE
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.blob import Blob


class BiiApiTest(TestWithMongo):
    _multiprocess_shared_ = True

    def setUp(self):
        self.store = MongoServerStore(self.conn, self.__class__.__name__)
        self.mother = ModelCreator(self.store)
        self.testUser = self.mother.make_test_user()
        self.service = BiiService(self.store, self.testUser.ID)

    def test_get_cells_snapshot_invalid_version(self):
        b = self.mother.make_block(self.testUser)
        version = BlockVersion(block=b.ID, time=1)
        self.assertRaises(NotFoundException, self.service.get_cells_snapshot, version)

    def testNotFoundExceptions(self):
        self.assertRaises(NotFoundException, self.service.get_cells_snapshot,
                          BlockVersion('user/user/block/master', 3))

    def test_get_version_by_tag(self):
        brl_block = BRLBlock('%s/%s/TestBlock/master' % (self.testUser.ID, self.testUser.ID))
        publish_request = PublishRequest(BlockVersion(brl_block, -1))
        publish_request.tag = STABLE
        publish_request.versiontag = 'mytag'
        publish_request.cells.append(SimpleCell(brl_block.block_name + 'r1.h'))
        publish_request.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        publish_request.deptable = BlockVersionTable()
        self.service.publish(publish_request)

        publish_request = PublishRequest(BlockVersion(brl_block, 0, 'mytag'))
        publish_request.tag = STABLE
        publish_request.versiontag = 'mytag'
        publish_request.cells.append(SimpleCell(brl_block.block_name + 'r12.h'))
        publish_request.contents['r2.h'] = Content(id_=None, load=Blob('hola'))
        publish_request.deptable = BlockVersionTable()
        self.service.publish(publish_request)

        block_version = self.service.get_version_by_tag(brl_block, 'mytag')
        self.assertEquals(1, block_version.time)

    def test_tag_nofound(self):
        brl_block = BRLBlock('%s/%s/TestBlock/master' % (self.testUser.ID, self.testUser.ID))
        with self.assertRaises(NotFoundException):
            self.service.get_version_by_tag(brl_block, 'mytag')
