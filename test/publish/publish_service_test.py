import unittest
from mock import Mock  # @UnresolvedImport
from biicode.server.publish.publish_service import PublishService
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.cells import SimpleCell
from biicode.common.model.content import Content
from biicode.common.exception import NotInStoreException, BiiException
from biicode.server.authorize import Security
from biicode.server.model.permissions.permissions import Permissions
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.server.store.generic_server_store import GenericServerStore
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.model.block import Block
from mock import patch
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.server.model.user import User
from biicode.test.testing_mem_server_store import TestingMemServerStore
from biicode.server.api.bii_service import BiiService
from biicode.common.model.blob import Blob
from biicode.common.model.version_tag import DEV
from biicode.common.exception import PublishException, ForbiddenException
from biicode.server.background.enqueuer import Enqueuer


class PublishServiceTest(unittest.TestCase):

    def test_publish_rejected(self):
        store = Mock(MongoServerStore)
        user = Mock()
        user.blocks = {}
        store.read_user = Mock(return_value=user)

        block = Mock(Block)
        block.add_publication.return_value = (Mock(), Mock())
        store.read_block.return_value = block
        brl = BRLBlock('user/user/block/branch')

        p = PublishService(store, 'authUser')
        pack = PublishRequest(BlockVersion(brl, -1))
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        pack.deptable = BlockVersionTable()
        with self.assertRaises(ForbiddenException):
            p.publish(pack)

    @patch.object(Enqueuer, "enqueue_job")
    def test_publish(self, enqueuer):
        brl = BRLBlock('owner/user/block/branch')
        # moduleID=BlockID(UserID(123),456)
        store = Mock(MongoServerStore)
        store.read_block_permissions = Mock(return_value=ElementPermissions(brl, private=False))
        user = User("owner")
        user.numeric_id = 1
        user.blocks = {}
        store.read_user = Mock(return_value=user)
        block = Mock(Block)
        block.last_version.return_value = Mock(BlockVersion)
        block.add_publication.return_value = (Mock(list), Mock(list), Mock(list), Mock(list))
        block.deltas = []

        ensure = Security('authUser', store)
        ensure.check_create_block = Mock(return_value=True)
        ensure.check_write_block = Mock(return_value=True)
        ensure.check_read_block = Mock(return_value=True)

        store.read_block.return_value = block
        store.read_published_cells.return_value = {}
        p = PublishService(store, 'authUser')
        p.security = ensure

        pack = PublishRequest(BlockVersion(brl, -1))
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        pack.cells.append(SimpleCell('user/block/r2.h'))
        pack.contents['r2.h'] = Content(id_=None, load=Blob('hola'))
        pack.cells.append(SimpleCell('user/block/r3.h'))
        pack.contents['r3.h'] = Content(id_=None, load=Blob('hola'))
        pack.deptable = BlockVersionTable()
        p.publish(pack)

        block.add_publication.assert_called_once_with(pack, p.auth_user)
        store.update_block.assert_called_once_with(block)
        self.assertEqual(1, store.create_published_cells.call_count)
        self.assertEqual(1, store.create_published_contents.call_count)

        # Check sizes
        self.assertEquals(user.blocks_bytes, 12)  # 12 bytes "hola" * 3

        # Publish again, see the size incremented
        pack._bytes = None  # Lazy computed
        p.publish(pack)
        self.assertEquals(user.blocks_bytes, 24)  # 24 bytes: "hola" * 3 * 2 publications

        # Max size exceeded for user
        user.max_workspace_size = 25
        self.assertRaises(ForbiddenException, p.publish, pack)

        # Try to publish only 1 byte
        pack._bytes = None  # Lazy computed
        pack.cells = []
        pack.contents = {}
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('h'))
        p.publish(pack)

    @patch.object(Enqueuer, "enqueue_job")
    def test_publish_no_contents(self, enqueuer):
        brl = BRLBlock('owner/user/block/branch')
        store = Mock(MongoServerStore)
        store.read_block_permissions = Mock(return_value=ElementPermissions(brl, private=False))

        p = PublishService(store, 'authUser')
        pack = PublishRequest(BlockVersion(brl, -1))
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        pack.versiontag = 'mytag'
        with self.assertRaisesRegexp(PublishException, 'DEV'):
            p.publish(pack)

    @patch.object(Enqueuer, "enqueue_job")
    def test_publish_dev_with_tag(self, enqueuer):
        brl = BRLBlock('owner/user/block/branch')
        store = Mock(MongoServerStore)
        store.read_block_permissions = Mock(return_value=ElementPermissions(brl, private=False))
        user = Mock()
        user.blocks = {}
        store.read_user = Mock(return_value=user)

        block = Mock(Block)
        block.add_publication.return_value = (['mock_id'], [], [], [])
        block.deltas = []
        ensure = Security('authUser', store)
        ensure.check_read_block = Mock(return_value=True)
        ensure.check_create_block = Mock(return_value=True)
        ensure.check_write_block = Mock(return_value=True)
        ensure.check_publish_block = Mock(return_value=True)

        store.read_block.return_value = block
        store.read_published_cells.return_value = {}
        p = PublishService(store, 'authUser')
        p.security = ensure
        pack = PublishRequest(BlockVersion(brl, -1))
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.deptable = BlockVersionTable()
        p.publish(pack)

    def test_publish_concurrent_modification(self):
        self.store = TestingMemServerStore()
        brl = 'user'
        self.store.create_user(User(brl))
        self.service = BiiService(self.store, brl)

        self.brl_block = BRLBlock('user/user/block/master')
        request = PublishRequest(BlockVersion(self.brl_block, -1))
        request.cells.append(SimpleCell('user/block/r1.h'))
        request.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        request.deptable = BlockVersionTable()
        request.tag = DEV
        self.service.publish(request)

        '''Branch 1 (from master) creates new resource'''
        self.brl_block1 = BRLBlock('user/user/block/branch1')
        request = PublishRequest(BlockVersion(self.brl_block, 0))
        request.cells.append(SimpleCell('user/block/r2.h'))
        request.contents['r2.h'] = Content(id_=None, load=Blob('adios'))
        request.deptable = BlockVersionTable()
        with self.assertRaisesRegexp(BiiException, 'Concurrent modification'):
            self.service.publish(request)

    def get_version_info_test(self):
        store = Mock(GenericServerStore)

        # Block doesn't exist and user is other
        p = PublishService(store, 'any_user')
        block_brl = BRLBlock("user/user/theblock/master")
        store.read_block_permissions = Mock(side_effect=NotInStoreException())
        block_info = p.get_block_info(block_brl)
        self.assertFalse(block_info.can_write)

        # Now block exists
        store.read_block_permissions = Mock(return_value=ElementPermissions(block_brl))

        # Block exists and user is the authorized one
        p = PublishService(store, 'theuser')
        block_brl = BRLBlock("theuser/theuser/theblock/master")
        block_info = p.get_block_info(block_brl)
        self.assertTrue(block_info.can_write)

        # No authorized write to an existing block
        p = PublishService(store, 'wronguser')
        user = Mock(User)
        user.administrators = Permissions()
        store.read_user = Mock(return_value=user)
        block_info = p.get_block_info(block_brl)
        self.assertFalse(block_info.can_write)

        # Authorized user with an existing block
        p = PublishService(store, 'theuser')
        block_brl = BRLBlock("theuser/theuser/theblock/master")
        block_info = p.get_block_info(block_brl)
        self.assertTrue(block_info.can_write)
