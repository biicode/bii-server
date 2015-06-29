from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.find.finder_request import FinderRequest
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.declare.cpp_declaration import CPPDeclaration
from biicode.common.find.policy import Policy
from biicode.server.test.find.finder_test import BaseFinderTest
from biicode.server.test.publisher import TestPublisher
from biicode.common.api.ui import BiiResponse


class MultipleFilesFinderTest(BaseFinderTest):
    '''This test use several files inside one block.
    Previously, all server Find tests where only with 1 file per block, and there was a nasty bug,
    that didn't find new includes once the first found was found
    '''

    def test_find_one_file_at_a_time(self):
        '''Starts with one include, finds it, then put another include, finish when all are found.
        Found items are taken into account in FindRequest.existing
        '''
        NUM_FILES = 10
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        publisher = TestPublisher(self.user, self.store)
        names_a = [BlockCellName(self.user + "/blocka/a%d.h" % i) for i in range(NUM_FILES)]
        resources_info = {"a%d.h" % i: ("a", []) for i in range(NUM_FILES)}
        publisher.publish(brl_a, resources_info)
        # Use the same request object, to accumulate existing (already found) files
        request = FinderRequest()
        request.policy = Policy.default()
        version = BlockVersion(brl_a, 0)  # The version is always the same
        for i in range(NUM_FILES):
            declaration = CPPDeclaration(names_a[i])
            request.unresolved = {declaration}
            result = self.service.find(request, BiiResponse())
            self.check_result(result, resolved=[(brl_a, 0, {names_a[i]})])
            # The found one is added to the existing, for next iteration
            request.existing[version][declaration] = {names_a[i]}
            self.assertEqual(len(request.existing[version]), i + 1)

    def test_find_two_files_at_a_time(self):
        """Starts with one include, finds it, then two more includes, finish when all are found.
        Found items are taken into account in FindRequest.existing
        """

        NUM_FILES = 10
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        names_a = [BlockCellName(self.user + "/blocka/a%d.h" % i) for i in range(NUM_FILES)]
        resources_info = {"a%d.h" % i: ("a", []) for i in range(NUM_FILES)}
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, resources_info)
        # Use the same request object, to accumulate existing (already found) files
        request = FinderRequest()
        request.policy = Policy.default()
        version = BlockVersion(brl_a, 0)  # The version is always the same
        for i in range(0, NUM_FILES, 2):
            declaration1 = CPPDeclaration(names_a[i])
            declaration2 = CPPDeclaration(names_a[i + 1])
            request.unresolved = {declaration1, declaration2}
            result = self.service.find(request, BiiResponse())
            self.check_result(result, resolved=[(brl_a, 0, {names_a[i], names_a[i + 1]})])
            # The found one is added to the existing, for next iteration
            request.existing[version][declaration1] = {names_a[i]}
            request.existing[version][declaration2] = {names_a[i + 1]}
            self.assertEqual(len(request.existing[version]), i + 2)

    def test_files_from_different_blocks(self):
        """This test solves the bug that appeared when user included 2 different headers
        from different blocks A, B, such A->B, and the files included were not modified among
        different versions.

        The problem was the finder discarding subsequent hypothesis because it thought they will
        be the same based on ids (cells, contents) and dep_table. This is not true, they might
        not have changed, but their dependencies have changed, so every block_version must have
        it's own hypothesis
        """
        brl_a = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        names = [BlockCellName(self.user + "/blocka/path/to/a%d.h" % i) for i in range(1, 3)]
        resources_info = {"path/to/a%d.h" % i: ("a", [names[0]] if i == 2 else [])
                          for i in range(1, 3)}
        publisher = TestPublisher(self.user, self.store)
        publisher.publish(brl_a, resources_info)
        version_a0 = BlockVersion(brl_a, 0)
        brl_b = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blockb'))
        publisher.publish(brl_b, {'path/to/b.h': ('b', [names[1]])}, dep_versions=version_a0)

        # publish 2 versions more of B, with a new file b2
        for i in range(2):
            publisher.publish(brl_b, {'path/to/b2.h': ('b', [])}, dep_versions=version_a0)

        #publish a new A version, changing file a1
        publisher.publish(brl_a, {'path/to/a1.h': ('a', [])})

        request = self.build_unresolved_request(['find_user/blocka/path/to/a2.h',
                                                 'find_user/blockb/path/to/b.h'])
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(brl_a, 0, {'find_user/blocka/path/to/a2.h'}),
                                            (brl_b, 2, {'find_user/blockb/path/to/b.h'})])
