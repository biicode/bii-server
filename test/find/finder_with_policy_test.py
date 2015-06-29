from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.find.policy import Policy
from biicode.server.test.find.finder_test import BaseFinderTest
from biicode.common.model.version_tag import DEV, ALPHA, STABLE, BETA
from biicode.server.test.publisher import TestPublisher
from biicode.common.api.ui import BiiResponse
import time


class FinderPolicyTest(BaseFinderTest):
    """ Single file, single block finds, playing with policies
    """

    def setUp(self):
        """basic setup and creation of 10 versions with DEV-ALPHA-BETA-STABLE-DEV...."""
        BaseFinderTest.setUp(self)
        self.name = BlockCellName(self.user + "/blocka/resourcename")
        self.brl = BRLBlock('%s/%s/%s/master' % (self.user, self.user, 'blocka'))
        publisher = TestPublisher(self.user, self.store)
        for tag in [STABLE, BETA, ALPHA, DEV]:
            time.sleep(0.05)
            publisher.publish(self.brl, {'resourcename': ('a', [])}, tag)

    def test_tag_policy_find(self):
        """ change tag policy to find BETA and DEV """
        request = self.build_unresolved_request(self.name)
        request.policy = Policy.loads("*: BETA")
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(self.brl, 1, {self.name})])

        request = self.build_unresolved_request(self.name)
        request.policy = Policy.loads("*: ALPHA")
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(self.brl, 2, {self.name})])

        request = self.build_unresolved_request(self.name)
        request.policy = Policy.loads("*: DEV")
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(self.brl, 3, {self.name})])

        request = self.build_unresolved_request(self.name)
        result = self.service.find(request, BiiResponse())
        self.check_result(result, resolved=[(self.brl, 0, {self.name})])

    def test_tag_policy_update(self):
        for i, tag in enumerate([BETA, ALPHA, DEV]):
            # Do not update
            request = self.build_update_request(BlockVersion(self.brl, i), self.name)
            result = self.service.find(request, BiiResponse())
            self.check_result(result)

            # update
            request.policy = Policy.loads("*: %s" % tag)
            result = self.service.find(request, BiiResponse())
            self.check_result(result, updated=[(self.brl, i + 1, {self.name})])
