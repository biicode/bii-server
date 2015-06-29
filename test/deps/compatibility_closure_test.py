import unittest

from biicode.common.model.symbolic.reference import References
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.server.deps.compatibility_closure import CompatibilityClosure
from biicode.common.model.id import ID
from biicode.common.exception import BiiException


class CompatibilityClosureTest(unittest.TestCase):

    def test_interface(self):
        cell_id1 = ID((0, 0, 0))
        content_id1 = ID((0, 0, 0))
        cell_id2 = ID((0, 1, 0))
        content_id2 = ID((0, 1, 0))
        brl0 = BRLBlock('user/user/block/master')
        brl1 = BRLBlock('user/user/block2/master')
        v0 = BlockVersion(brl0, 0)
        v1 = BlockVersion(brl0, 1)
        v2 = BlockVersion(brl1, 0)

        c1 = CompatibilityClosure()
        c1.add_item((cell_id1, content_id1),  cell_id1, v0, 'file1')
        self.assertEqual("{0:0:0: ((0:0:0, 0:0:0), user/block: 0, 'file1')}", str(c1))

        # adding a compatible item is no problem
        c1.add_item((cell_id1, content_id1),  cell_id1, v1, 'file1')
        self.assertEqual("{0:0:0: ((0:0:0, 0:0:0), user/block: 1, 'file1')}", str(c1))

        c1.add_item((cell_id2, content_id2),  cell_id2, v2, 'file2')
        self.assertIn("0:0:0: ((0:0:0, 0:0:0), user/block: 1, 'file1')", str(c1))
        self.assertIn("0:1:0: ((0:1:0, 0:1:0), user/block2: 0, 'file2')", str(c1))

        self.assertEqual({v0.block_name + 'file1', v2.block_name + 'file2'}, c1.block_cell_names)

        refs = References()
        refs[v1].add('file1')
        refs[v2].add('file2')
        self.assertEqual(refs, c1.references)

    def test_empty(self):
        '''when one is empty, always compatible'''
        c1 = CompatibilityClosure()
        c2 = CompatibilityClosure()
        self.assertEqual(0, c1.conflicts(c2))
        self.assertEqual(0, c2.conflicts(c1))

        brl0 = BRLBlock('user/user/block/master')
        brl1 = BRLBlock('user/user/block2/master')
        v0 = BlockVersion(brl0, 0)
        v2 = BlockVersion(brl1, 0)

        cell_id1 = ID((0, 0, 0))
        cell_id2 = ID((0, 0, 1))

        content_id1 = ID((0, 0, 0))
        content_id2 = ID((0, 0, 1))

        c1.add_item((cell_id1, content_id1),  cell_id1, v0, 'file1')
        self.assertEqual(0, c1.conflicts(c2))
        self.assertEqual(0, c2.conflicts(c1))

        c1.add_item((cell_id2, content_id2),  cell_id2, v2, 'file2')
        self.assertEqual(0, c1.conflicts(c2))
        self.assertEqual(0, c2.conflicts(c1))

    def test_compatible(self):
        c1 = CompatibilityClosure()
        c2 = CompatibilityClosure()

        brl0 = BRLBlock('user/user/block/master')
        brl1 = BRLBlock('user/user/block2/master')
        v0 = BlockVersion(brl0, 0)
        v1 = BlockVersion(brl0, 1)
        v2 = BlockVersion(brl1, 0)
        v3 = BlockVersion(brl1, 1)

        cell_id1 = ID((0, 0, 0))
        cell_id2 = ID((0, 0, 1))

        content_id1 = ID((0, 0, 0))
        content_id2 = ID((0, 0, 1))

        c1.add_item((cell_id1, content_id1),  cell_id1, v0, 'file1')
        c2.add_item((cell_id1, content_id1),  cell_id1, v1, 'file1')
        self.assertEqual(0, c1.conflicts(c2))
        self.assertEqual(0, c2.conflicts(c1))

        c1.add_item((cell_id2, content_id2),  cell_id2, v2, 'file2')
        c2.add_item((cell_id2, content_id2),  cell_id2, v3, 'file2')
        self.assertEqual(0, c1.conflicts(c2))
        self.assertEqual(0, c2.conflicts(c1))

    def test_incompatible(self):
        c1 = CompatibilityClosure()
        c2 = CompatibilityClosure()

        brl0 = BRLBlock('user/user/block/master')
        v0 = BlockVersion(brl0, 0)
        v1 = BlockVersion(brl0, 1)

        cell_id1 = ID((0, 0, 0))
        cell_id2 = ID((0, 0, 1))

        content_id1 = ID((0, 0, 0))

        c1.add_item((cell_id1, content_id1),  cell_id1, v0, 'file1')
        c2.add_item((cell_id2, content_id1),  cell_id1, v1, 'file1')
        self.assertEqual(1, c1.conflicts(c2))
        self.assertEqual(1, c2.conflicts(c1))

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
