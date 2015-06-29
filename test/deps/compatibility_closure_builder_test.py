import unittest
from mock import Mock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.reference import References, Reference, ReferencedResources
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.server.deps.compatibility_closure_builder import build_compatibility_closure
from biicode.server.deps.compatibility_closure import CompatibilityClosure
from biicode.common.deps.block_version_graph import BlockVersionGraph


class CompatibilityClosureBuilderTest(unittest.TestCase):

    def test_build_closure_different_versions(self):
        '''Computes a CompatibilityClosure in which two versions of blockA actually point to the
        same unmodified resource with the typical diamond layout
        Also computes and checks the BlockClosure for that layout'''
        ref_translator = Mock()

        depA1 = BlockVersion(BRLBlock('user/user/blockA/branch'), 4)
        depA2 = BlockVersion(BRLBlock('user/user/blockA/branch'), 5)
        baseB = BlockVersion(BRLBlock('user/user/blockB/branch'), 2)
        baseC = BlockVersion(BRLBlock('user/user/blockC/branch'), 3)

        full_graph = BlockVersionGraph()
        full_graph.add_nodes([baseB, baseC, depA1, depA2])
        full_graph.add_edge(baseB, depA1)
        full_graph.add_edge(baseC, depA2)

        def res_method(*args):
            depsb = [BlockCellName('user/blockA/a.h')]
            depsc = [BlockCellName('user/blockA/a.h')]
            result = ReferencedResources()
            for ref in args[0].explode():
                result[ref.block_version][ref.ref] = \
                {Reference(depA1, 'a.h'): ((0, 0), 0, []),
                 Reference(depA2, 'a.h'): ((0, 0), 0, []),
                 Reference(baseB, 'b.h'): ((1, 4), 1, depsb),
                 Reference(baseC, 'c.h'): ((2, 3), 2, depsc)}[ref]
            return result

        ref_translator.get_published_min_refs.side_effect = res_method

        missing = References()
        missing.add(Reference(baseB, 'b.h'))
        missing.add(Reference(baseC, 'c.h'))
        closure = CompatibilityClosure(missing)
        build_compatibility_closure(ref_translator, closure, full_graph.nodes, full_graph)

        self.assertEqual(References(), closure.broken)
        self.assertEqual(set([BlockCellName('user/blockA/a.h'),
                              BlockCellName('user/blockB/b.h'),
                              BlockCellName('user/blockC/c.h')]),
                              closure.block_cell_names)
        #self.assertIn(Reference(depA1, 'a.h'), closure.references)
        self.assertIn(baseB, closure.references)
        self.assertIn(baseC, closure.references)

    def test_broken_closure(self):
        '''computes a closure in which cell blockB/b.h depends on blockA/a.h, but that a.h
        is not found. The algorithms of closures must return that as a missing or broken dependency

        '''
        ref_translator = Mock()
        baseB = BlockVersion(BRLBlock('user/user/blockB/branch'), 2)
        depA1 = BlockVersion(BRLBlock('user/user/blockA/branch'), 4)

        full_graph = BlockVersionGraph()
        full_graph.add_nodes([baseB, depA1])
        full_graph.add_edge(baseB, depA1)

        def res_method(*args):
            depsb = [BlockCellName('user/blockA/a.h')]

            result = ReferencedResources()
            for ref in args[0].explode():
                try:
                    result[ref.block_version][ref.ref] = \
                    {
                     Reference(baseB, 'b.h'): ((0, 0), 0, depsb),
                     }[ref]
                except KeyError:
                    pass
            return result

        ref_translator.get_published_min_refs.side_effect = res_method

        missing = References()
        missing.add(Reference(baseB, 'b.h'))
        closure = CompatibilityClosure(missing)
        build_compatibility_closure(ref_translator, closure, full_graph.nodes, full_graph)

        self.assertEqual({BlockCellName('user/blockB/b.h')}, closure.block_cell_names)
        self.assertIn(baseB, closure.references)

        expected_missing = References()
        expected_missing[depA1].add('a.h')
        self.assertEqual(closure.broken, expected_missing)

    def _virtual_setup(self):
        ref_translator = Mock()
        depA = BlockVersion(BRLBlock('user/user/blockA/branch'), 4)
        depB = BlockVersion(BRLBlock('user/user/blockB/branch'), 2)
        baseC = BlockVersion(BRLBlock('user/user/blockC/branch'), 3)

        full_graph = BlockVersionGraph()
        full_graph.add_nodes([baseC, depA, depB])
        full_graph.add_edge(baseC, depA)
        full_graph.add_edge(baseC, depB)

        def res_method(*args):
            c_virtual_leaves = [BlockCellName('user/blockC/win/c.h'),
                                BlockCellName('user/blockC/nix/c.h')]
            c_win_deps = [BlockCellName('user/blockA/a.h')]
            c_nix_deps = [BlockCellName('user/blockB/b.h')]

            result = ReferencedResources()
            for ref in args[0].explode():
                result[ref.block_version][ref.ref] = \
                {Reference(depA, 'a.h'): ((0, 0), 0, []),
                 Reference(depB, 'b.h'): ((1, 1), 1, []),
                 Reference(baseC, 'c.h'): ((2, 2), 2, c_virtual_leaves),
                 Reference(baseC, 'win/c.h'): ((3, 3), 3, c_win_deps),
                 Reference(baseC, 'nix/c.h'): ((4, 4), 4, c_nix_deps)}[ref]
            return result

        ref_translator.get_published_min_refs.side_effect = res_method
        return ref_translator, depA, depB, baseC, full_graph

    def test_virtual_no_settings(self):
        '''builds a very simple closure in which virtual cells are involved. Maybe it is not very
        useful, as now virtuality is not handled at this level, only at the MemServerStore level,
        so this test might be redundant'''
        ref_translator, depA, depB, baseC, full_graph = self._virtual_setup()

        missing = References()
        missing.add(Reference(baseC, 'c.h'))
        closure = CompatibilityClosure(missing)
        build_compatibility_closure(ref_translator, closure, full_graph.nodes, full_graph)
        self.assertEqual(References(), closure.broken)

        self.assertEqual(set([BlockCellName('user/blockA/a.h'),
                              BlockCellName('user/blockB/b.h'),
                              BlockCellName('user/blockC/c.h'),
                              BlockCellName('user/blockC/win/c.h'),
                              BlockCellName('user/blockC/nix/c.h')]),
                              closure.block_cell_names)

    def test_build_closure_different_versions_restricted(self):
        '''Computes a CompatibilityClosure in which two versions of blockA actually point to the
        same unmodified resource with the typical diamond layout
        Also computes and checks the BlockClosure for that layout'''
        ref_translator = Mock()

        depA1 = BlockVersion(BRLBlock('user/user/blockA/branch'), 4)
        depA2 = BlockVersion(BRLBlock('user/user/blockA/branch'), 5)
        baseB = BlockVersion(BRLBlock('user/user/blockB/branch'), 2)
        baseC = BlockVersion(BRLBlock('user/user/blockC/branch'), 3)

        full_graph = BlockVersionGraph()
        full_graph.add_nodes([baseB, baseC, depA1, depA2])
        full_graph.add_edge(baseB, depA1)
        full_graph.add_edge(baseC, depA2)

        def res_method(*args):
            depsb = [BlockCellName('user/blockA/a.h')]
            depsc = [BlockCellName('user/blockA/a.h')]
            result = ReferencedResources()
            for ref in args[0].explode():
                result[ref.block_version][ref.ref] = \
                {Reference(depA1, 'a.h'): ((0, 0), 0, []),
                 Reference(depA2, 'a.h'): ((0, 0), 0, []),
                 Reference(baseB, 'b.h'): ((1, 4), 1, depsb),
                 Reference(baseC, 'c.h'): ((2, 3), 2, depsc)}[ref]
            return result

        ref_translator.get_published_min_refs.side_effect = res_method

        missing = References()
        missing.add(Reference(baseB, 'b.h'))
        missing.add(Reference(baseC, 'c.h'))
        closure = CompatibilityClosure(missing)
        build_compatibility_closure(ref_translator, closure, {baseC}, full_graph)

        self.assertEqual(References(), closure.broken)
        self.assertEqual({BlockCellName('user/blockC/c.h')}, closure.block_cell_names)
        #self.assertIn(Reference(depA1, 'a.h'), closure.references)
        self.assertNotIn(baseB, closure.references)
        self.assertNotIn(depA1, closure.references)
        self.assertNotIn(depA2, closure.references)
        self.assertIn(baseC, closure.references)
        expected_frontier = References()
        expected_frontier[baseB].add('b.h')
        expected_frontier[depA2].add('a.h')
        self.assertEqual(expected_frontier, closure.frontier)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_simple']
    unittest.main()
