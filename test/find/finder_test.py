import unittest
from biicode.test.testing_mem_server_store import TestingMemServerStore
from biicode.server.model.user import User
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.brl.brl_user import BRLUser
from biicode.server.api.bii_service import BiiService
from biicode.common.find.finder_request import FinderRequest
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.symbolic.reference import ReferencedDependencies
from biicode.common.model.declare.cpp_declaration import CPPDeclaration
from biicode.common.find.policy import Policy
from biicode.server.test.publisher import TestPublisher
from biicode.common.api.ui import BiiResponse
import time


class BaseFinderTest(unittest.TestCase):
    def setUp(self):
        """ all find tests have a user, store, and BiiService """
        self.user = BRLUser('find_user')
        self.store = TestingMemServerStore()
        user = User(self.user)
        user.password = 'password'
        self.store.create_user(user)
        self.service = BiiService(self.store, self.user)

    def check_result(self, result, resolved=None, unresolved=None, updated=None):
        unresolved = unresolved or []
        unresolved = {CPPDeclaration(str(u)) for u in unresolved}
        self.assertEqual(result.unresolved, unresolved)

        resolved = resolved or []
        refs = ReferencedDependencies()
        for brl, time, block_cell_names in resolved:
            for name in block_cell_names:
                refs[BlockVersion(brl, time)][CPPDeclaration(name)] = {BlockCellName(name)}
        self.assertEqual(result.resolved, refs)

        updated = updated or []
        refs = ReferencedDependencies()
        for brl, time, block_cell_names in updated:
            for name in block_cell_names:
                refs[BlockVersion(brl, time)][CPPDeclaration(name)] = {BlockCellName(name)}
        self.assertEqual(result.updated, refs)

    def build_unresolved_request(self, unresolved_deps):
        if isinstance(unresolved_deps, basestring):
            unresolved_deps = [unresolved_deps]
        request = FinderRequest()
        unresolved = set()
        for dep in unresolved_deps:
            unresolved.add(CPPDeclaration(dep))
        request.unresolved = unresolved
        request.policy = Policy.default()
        return request

    def build_update_request(self, block_version, block_cell_name):
        request = FinderRequest()
        existing = ReferencedDependencies()
        existing[block_version][CPPDeclaration(block_cell_name)].add(block_cell_name)
        request.existing = existing
        request.policy = Policy.default()
        request.find = False
        request.update = True
        return request


class FinderTest(BaseFinderTest):
    """ Find tests with 1 single file per block """

    def test_simple_find(self):
        '''Test including a single block with 1 file 1 version without further dependencies,
        always last version
        '''
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        for i in range(4):
            publisher.publish(brl_a, {'a.h': ('a', [])})
            # self.publish(brl_a, name_a)
            request = self.build_unresolved_request(name_a)
            result = self.service.find(request, BiiResponse())
            self.check_result(result, resolved=[(brl_a, i, {name_a})])

    def test_simple_update(self):
        '''Test finding updates in a simple block with 1 file with no more dependencies '''
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, {'a.h': ('a', [])})

        #self.publish(brl_a, name_a)
        for i in range(1, 10):
            time.sleep(0.05)
            publisher.publish(brl_a, {'a.h': ('a', [])})
            #self.publish(brl_a, name_a)
            request = self.build_update_request(BlockVersion(brl_a, i - 1), name_a)
            result = self.service.find(request, BiiResponse())
            ref_updated = [(brl_a, i, {name_a})]
            self.check_result(result, updated=ref_updated)

    def test_disallow_cycles(self):
        """ a find cannot return a block that is already in the src blocks of the hive """
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, {'a.h': ('a', [])})
        request = self.build_unresolved_request(name_a)
        request.block_names.add(name_a.block_name)
        response = BiiResponse()
        result = self.service.find(request, response)
        # TODO: return a message to user saying that it is because a cycle
        self.assertIn('No block candidates found', str(response))
        self.check_result(result, unresolved=request.unresolved)

    def test_find_transitive(self):
        '''Test including a block with other dependencies, without conflicts '''
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, {'a.h': ('a', [])})

        brl_b = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blockb'))
        name_b = BlockCellName(self.user + "/blockb/b.h")
        #self.publish(brl_b, name_b, deps={name_b: name_a}, dep_versions=BlockVersion(brl_a, 0))
        publisher.publish(brl_b, {'b.h': ('b', [name_a])},
                          dep_versions=BlockVersion(brl_a, 0))

        request = self.build_unresolved_request(name_b)
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(brl_b, 0, {name_b})])

    def test_diamond_single_solution(self):
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        brl_b = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blockb'))
        brl_c = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blockc'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        for _ in range(20):
            publisher.publish(brl_a, {'a.h': ('a', [])})

        name_b = BlockCellName(self.user + "/blockb/b.h")
        name_c = BlockCellName(self.user + "/blockc/c.h")

        for i in range(0, 20):
            if i % 2 == 0:
                publisher.publish(brl_b, {'b.h': ('b', [name_a])},
                                  dep_versions=BlockVersion(brl_a, i))
            if (i % 2 == 1 or i == 10):
                publisher.publish(brl_c, {'c.h': ('c', [name_a])},
                                  dep_versions=BlockVersion(brl_a, i))

        request = self.build_unresolved_request([name_b, name_c])
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(brl_b, 5, {name_b}), (brl_c, 5, {name_c})])

    def test_disallow_cycles_transitive(self):
        """ A find must not find any block name that is in the current src blocks, even
        transitively.
        """
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        name_a = BlockCellName(self.user + "/blocka/a.h")
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, {'a.h': ('a', [])})

        brl_b = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blockb'))
        name_b = BlockCellName(self.user + "/blockb/b.h")
        publisher.publish(brl_b, {'b.h': ('b', [name_a])}, dep_versions=BlockVersion(brl_a, 0))

        request = self.build_unresolved_request(name_b)
        request.block_names.add(name_a.block_name)
        response = BiiResponse()
        result = self.service.find(request, response)
        self.assertIn("Can't find a compatible solution", str(response))
        self.assertIn('it has cycles', str(response))
        self.check_result(result, unresolved=request.unresolved)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
