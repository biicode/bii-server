import unittest
from biicode.server.model.block import Block
from biicode.common.model.id import ID, UserID
from biicode.common.model.cells import SimpleCell
from biicode.common.model.content import Content
from biicode.common.model.brl.cell_name import CellName
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.renames import Renames
from biicode.common.model.version_tag import STABLE


class BlockTest(unittest.TestCase):

    def setUp(self):
        self.block_id = ID((1, 2))
        self.block = Block(self.block_id, None)
        self.brl = BRLBlock("user/user/block/master")

    def test_new_cell(self):
        publish_request = PublishRequest(BlockVersion(self.brl, -1))
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        self.block.add_publication(publish_request)
        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.cells.get_all_ids(0))
        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.cells.get_all_ids(100))
        self.assertEquals({'r1.h': ID(self.block_id + 0)}, self.block.last_version_cells())

    def test_add_modify_cell(self):
        publish_request = PublishRequest(BlockVersion(self.brl, -1))
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.cells.get_all_ids(0))

        publish_request = PublishRequest(BlockVersion(self.brl, 0))
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.cells.get_all_ids(0))
        self.assertEqual({'r1.h': ID(self.block_id + 1)}, self.block.cells.get_all_ids(1))
        self.assertEqual({'r1.h': ID(self.block_id + 1)}, self.block.last_version_cells())

    def test_add_delete_cell(self):
        publish_request = PublishRequest(BlockVersion(self.brl, -1))
        publish_request.tag = STABLE
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        publish_request.contents['r1.h'] = Content(id_=None, load=None)
        self.block.add_publication(publish_request)

        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.cells.get_all_ids(0))
        self.assertEqual({'r1.h': ID(self.block_id + 0)}, self.block.contents.get_all_ids(0))

        publish_request = PublishRequest(BlockVersion(self.brl, 0))
        publish_request.tag = STABLE
        publish_request.deleted.append('r1.h')
        self.block.add_publication(publish_request)

        self.assertEqual({'r1.h': self.block_id + 0}, self.block.cells.get_all_ids(0))
        self.assertEqual({'r1.h': self.block_id + 0}, self.block.contents.get_all_ids(0))

        self.assertEqual({}, self.block.cells.get_all_ids(1))
        self.assertEqual({}, self.block.contents.get_all_ids(1))
        self.assertEqual({}, self.block.last_version_cells())

    def test_add_modify_delete_cell(self):
        publish_request = PublishRequest(BlockVersion(self.brl, -1))
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        publish_request.cells.append(SimpleCell('user/block/r2.h'))
        publish_request.cells.append(SimpleCell('user/block/r3.h'))
        publish_request.contents['r1.h'] = Content(id_=None, load=None)
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        ids0 = set(self.block.cells.get_all_ids(0).values())
        names0 = set(self.block.cells.get_all_ids(0).keys())
        expected_ids0 = set([ID(self.block_id + 0), ID(self.block_id + 1), ID(self.block_id + 2)])
        expected_names0 = set(['r1.h', 'r2.h', 'r3.h'])
        self.assertEqual(expected_ids0, ids0)
        self.assertEqual(expected_names0, names0)

        publish_request = PublishRequest(BlockVersion(self.brl, 0))
        publish_request.deleted.append('r1.h')
        publish_request.cells.append(SimpleCell('user/block/r2.h'))
        publish_request.cells.append(SimpleCell('user/block/r4.h'))
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        self.assertEqual(expected_ids0, ids0)
        self.assertEqual(expected_names0, names0)

        prev = self.block.cells.get_all_ids(0)
        id3 = prev['r3.h']
        expected = set([id3, ID(self.block_id + 3), ID(self.block_id + 4)])
        self.assertEqual(expected, set(self.block.cells.get_all_ids(1).values()))
        expected = set(['r4.h', 'r2.h', 'r3.h'])
        self.assertEqual(expected, set(self.block.cells.get_all_ids(1).keys()))
        self.assertEqual(expected, set(self.block.last_version_cells().keys()))

    def test_renames(self):
        publish_request = PublishRequest(BlockVersion(self.brl, -1))
        publish_request.cells.append(SimpleCell('user/block/r1.h'))
        publish_request.contents['r1.h'] = Content(id_=None, load=None)
        publish_request.cells.append(SimpleCell('user/block/r2.h'))
        publish_request.contents['r2.h'] = Content(id_=None, load=None)
        publish_request.cells.append(SimpleCell('user/block/r3.h'))
        publish_request.contents['r3.h'] = Content(id_=None, load=None)
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        publish_request = PublishRequest(BlockVersion(self.brl, 0))
        publish_request.cells.append(SimpleCell('user/block/r11.h'))
        publish_request.deleted.append('r1.h')
        publish_request.renames = Renames({CellName('r1.h'): CellName('r11.h')})
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        publish_request = PublishRequest(BlockVersion(self.brl, 1))
        publish_request.cells.append(SimpleCell('user/block/r21.h'))
        publish_request.deleted.append('r2.h')
        publish_request.renames = Renames({CellName('r2.h'): CellName('r21.h')})
        publish_request.tag = STABLE
        self.block.add_publication(publish_request)

        self.assertEquals({}, self.block.get_renames(0, 0))
        self.assertEquals({'r1.h': 'r11.h'}, self.block.get_renames(0, 1))
        self.assertEquals({'r2.h': 'r21.h', 'r1.h': 'r11.h'}, self.block.get_renames(0, 2))


if __name__ == "__main__":

    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)
