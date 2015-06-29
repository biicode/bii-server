import unittest
from biicode.server.model.user import User
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.symbolic.reference import References
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.dependency_set import DependencySet
from biicode.server.reference_translator.reference_translator_service import \
                                                                ReferenceTranslatorService
import sys
import time
from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.common.model.declare.cpp_declaration import CPPDeclaration
from biicode.server.deps.compatibility_closure_builder import build_compatibility_closure
from biicode.server.deps.compatibility_closure import CompatibilityClosure
from biicode.server.store.mem_server_store import MemServerStore
from biicode.test.testing_mem_server_store import TestingMemServerStore
from biicode.common.deps.block_version_graph import BlockVersionGraph
from biicode.server.test.publisher import TestPublisher
from nose.plugins.attrib import attr


class CompatibilityClosureBuilderTest(TestWithMongo):

    def test_basic(self):
        store = TestingMemServerStore()
        brl_user = 'user'
        store.create_user(User(brl_user))
        brl_block = BRLBlock('user/user/block/master')
        publisher = TestPublisher(brl_user, store)
        publisher.publish(brl_block, {'r1.h': ('r1', ['user/block/r2.h']),
                                      'r2.h': ('r2', []),
                                      'r3.h': ('r3', [])})

        store = MemServerStore(store)
        translator = ReferenceTranslatorService(store, brl_user)
        ver = BlockVersion(brl_block, 0)
        missing = References()
        missing[ver].add('r1.h')
        closure = CompatibilityClosure(missing)
        full_graph = BlockVersionGraph()
        full_graph.add_nodes([ver])
        build_compatibility_closure(translator, closure, {ver}, full_graph)
        self.assertEqual(References(), closure.broken)

        expected = set()
        expected.add('user/block/r1.h')
        expected.add('user/block/r2.h')
        self.assertEqual(expected, closure.block_cell_names)

    def get_timer(self):
        if sys.platform == 'win32':
            # On Windows, the best timer is time.clock
            default_timer = time.clock
        else:
            # On most other platforms the best timer is time.time
            default_timer = time.time
        return default_timer

    @attr('performance')
    def test_performance_depth(self):
        brl_user = 'user'
        store = MongoServerStore(self.conn, self.__class__.__name__)
        store.create_user(User(brl_user))
        publisher = TestPublisher(brl_user, store)
        brl_block = BRLBlock('user/user/block/master')

        count = 500
        resource_info = {'cell%d.h' % i: ('content %d' % i,
                                          ['user/block/cell%d.h' % (i - 1)] if i else [])
                          for i in range(count)}
        publisher.publish(brl_block, resource_info)

        timer = self.get_timer()
        start_time = timer()
        # prof = cProfile.Profile()
        # prof.enable()
        store = MemServerStore(store)
        # print 'MEMSTORE DEPTH SIZE 0', asizeof(store) / 1000000.0
        translator = ReferenceTranslatorService(store, brl_user)
        version = BlockVersion(brl_block, 0)
        missing = References()
        missing[version].add('cell%d.h' % (count - 1))
        closure = CompatibilityClosure(missing)
        full_graph = BlockVersionGraph()
        full_graph.add_nodes([version])
        build_compatibility_closure(translator, closure, [version], full_graph)
        self.assertEqual(References(), closure.broken)
        #print 'CLOSURE SIZE ', asizeof(closure) / 1000000.0
        #print 'MEMSTORE SIZE ', asizeof(store) / 1000000.0
        elapsed_time = timer() - start_time
        #print 'Closure time', elapsed_time

        self.assertEqual({brl_block.block_name + c for c in resource_info},
                         closure.block_cell_names)
        self.assertLess(elapsed_time, 5)

    @attr('performance')
    def test_performance_breadth(self):
        store = MongoServerStore(self.conn, self.__class__.__name__)
        store.create_user(User("user2"))
        publisher = TestPublisher("user2", store)
        brl_block = BRLBlock('user2/user2/block/master')

        count = 1000
        resource_info = {}
        for i in xrange(count):
            deps = DependencySet()
            if i > 0:
                deps = DependencySet()
                for j in range(max(0, i - 25), i):
                    deps.explicit.add(BlockCellName('user2/block/cell%d.h' % j))
                    deps.resolved.add(CPPDeclaration('user2/block/cell%d.h' % j))
                deps.unresolved.add(CPPDeclaration('path/to/file.h'))
                deps.implicit.add(BlockCellName('user2/block/cell%d.h' % j))
            resource_info['cell%d.h' % i] = 'content %d' % i, deps
        publisher.publish(brl_block, resource_info)

        timer = self.get_timer()
        start_time = timer()

        store = MemServerStore(store)
        #print 'MEMSTORE SIZE 0', asizeof(store) / 1000000.0

        translator = ReferenceTranslatorService(store, "user2")
        version = BlockVersion(brl_block, 0)
        missing = References()
        missing[version].add('cell%d.h' % (count - 1))
        closure = CompatibilityClosure(missing)
        full_graph = BlockVersionGraph()
        full_graph.add_nodes([version])
        build_compatibility_closure(translator, closure, [version], full_graph)

        elapsed_time = timer() - start_time
        #print 'Closure time', elapsed_time

        #print 'CLOSURE SIZE ', asizeof(closure) / 1000000.0
        #print 'MEMSTORE SIZE ', asizeof(store) / 1000000.0
        # print 'MINCELLS SIZE ', asizeof(store.min_cells)/1000000.0

        self.assertEqual({brl_block.block_name + c for c in resource_info},
                         closure.block_cell_names)
        self.assertLess(elapsed_time, 7)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
