import unittest
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.server.authorize import Security, PlanUpgradeNeeded
from biicode.test.testing_mem_server_store import TestingMemServerStore
from biicode.server.model.user import User
from biicode.common.exception import ForbiddenException
from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.cells import SimpleCell
from biicode.common.model.content import Content
from biicode.common.model.blob import Blob


class AuthorizeTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.store = TestingMemServerStore()
        self.store.create_user(User("goku"))
        self.store.create_user(User("krilin"))
        self.store.create_user(User("freezer"))
        self.store.create_user(User("bulma"))

        self.public_brl = BRLBlock("goku/goku/block/ballno1")
        bper = ElementPermissions(self.public_brl, private=False)
        self.store.upsert_block_permissions(bper)

        goku = self.store.read_user("goku")
        goku.add_block(self.public_brl)
        self.store.update_user(goku)

    # TODO: Test num_user limits and message given to user!!!!!!

    def test_anonymous_operations(self):
        ensure = Security(None, self.store)
        ensure.check_read_block(self.public_brl)

    def test_check_make_private_block(self):
        # 0. Goku is paying
        self._subscribe("goku", "enterprise_275_50_x")

        # 1. Already private.
        brl_master = BRLBlock("goku/goku/block/master")
        bper_master = ElementPermissions(brl_master, private=True)
        self.store.upsert_block_permissions(bper_master)

        # 2. Bulma cant make it private even its already private because is not an admin
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "personal_7_1_x")
        self.assertRaises(ForbiddenException, ensure.check_make_private_a_block, "goku")

        # 3. Now block is public, so bulma can't make it private
        bper_master = ElementPermissions(brl_master, private=False)
        self.store.upsert_block_permissions(bper_master)
        self.assertRaises(ForbiddenException, ensure.check_make_private_a_block, "goku")

        # 4. Grant read and write, and bulma still can't make it private
        bper_master.read.grant("bulma")
        bper_master.write.grant("bulma")
        self.store.upsert_block_permissions(bper_master)
        self.assertRaises(ForbiddenException, ensure.check_make_private_a_block, "goku")

        # 5. Make bulma an admin, now bulma can make it private
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_make_private_a_block("goku")

        # 6. Bulma cant make private the block when suscription is not active
        self._subscribe("goku", "free")
        self.assertRaises(ForbiddenException, ensure.check_make_private_a_block, "goku")

    def test_check_make_public_block(self):

        # 1. Already public.
        brl_master = BRLBlock("goku/goku/block/master")
        bper_master = ElementPermissions(brl_master, private=False)
        self.store.upsert_block_permissions(bper_master)

        # 2. Bulma cant make it public even its already public
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_make_private_a_block, "goku")

        # 3. Now block is public, so bulma cant make it public
        bper_master = ElementPermissions(brl_master, private=True)
        self.store.upsert_block_permissions(bper_master)
        self.assertRaises(ForbiddenException, ensure.check_make_public_a_block, "goku")

        # 4. Grant read and write, and bulma still cant make it public
        bper_master.read.grant("bulma")
        bper_master.write.grant("bulma")
        self.store.upsert_block_permissions(bper_master)
        self.assertRaises(ForbiddenException, ensure.check_make_public_a_block, "goku")

        # 5. Make bulma an admin, now bulma can make it public
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_make_public_a_block("goku")

        # 5. Bulma can make public the block even when suscription is not active
        self._subscribe("bulma", "free")
        goku = self.store.read_user("goku")
        self.store.update_user(goku)
        ensure.check_make_public_a_block("goku")

    def test_read_block(self):

        # 1. Check we can always access a public block
        brl = BRLBlock("goku/goku/block/master")
        bper = ElementPermissions(brl, private=False)
        self.store.upsert_block_permissions(bper)

        ensure = Security("freezer", self.store)
        self._subscribe("freezer", "enterprise_275_50_x")
        ensure.check_read_block(brl)

        # Even owner is not paying
        self._subscribe("freezer", "free")
        ensure.check_read_block(brl)
        self._subscribe("freezer", "enterprise_275_50_x")

        # 2. Check we can read a private block due to being the owner
        bper = ElementPermissions(brl, private=True)
        self.store.upsert_block_permissions(bper)

        ensure = Security("goku", self.store)
        self._subscribe("freezer", "enterprise_275_50_x")
        ensure.check_read_block(brl)

        # 4. Check we can read the block even subscription is not valid
        self._subscribe("freezer", "free")
        ensure.check_read_block(brl)

        # 5. A user without read permissions cant read the block
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_read_block, brl)

        # 6. Until is granted as administrator or read granted
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_read_block(brl)
        goku.administrators.revoke("bulma")
        self.store.update_user(goku)
        self.assertRaises(ForbiddenException, ensure.check_read_block, brl)

        bper = ElementPermissions(brl, private=True)
        bper.read.grant("bulma")
        self.store.upsert_block_permissions(bper)
        ensure.check_read_block(brl)
        bper.read.remove("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_read_block, brl)

    def test_write_block(self):
        # 1. Onwer can write the block if its private
        brl = BRLBlock("goku/goku/block/master")
        self._add_block_to_user("goku", brl, True)

        ensure = Security("goku", self.store)
        self._subscribe("goku", "enterprise_275_50_x")
        ensure.check_write_block(brl)

        # If the owner is not paying he can't write
        ensure = Security("goku", self.store)
        self._subscribe("goku", "free")
        self.assertRaises(ForbiddenException, ensure.check_write_block, brl)
        self._subscribe("goku", "enterprise_275_50_x")

        # 1b. But other not granted user can't write
        ensure = Security("freezer", self.store)
        self._subscribe("freezer", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_write_block, brl)

        # 2. If bulma is granted as administrator or write he can write
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "enterprise_275_50_x")
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_write_block(brl)
        goku.administrators.revoke("bulma")
        self.store.update_user(goku)
        self.assertRaises(ForbiddenException, ensure.check_write_block, brl)

        bper = ElementPermissions(brl, private=True)
        bper.write.grant("bulma")
        self.store.upsert_block_permissions(bper)
        ensure.check_write_block(brl)
        bper.write.remove("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_write_block, brl)

        # 3. If we give read permissions only, user cant write
        bper = ElementPermissions(brl, private=True)
        bper.read.grant("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_write_block, brl)

    def test_delete_block(self):
        # First create master block permissions. Public
        brl = BRLBlock("goku/goku/block/master")
        bper_master = ElementPermissions(brl, private=True)
        self.store.upsert_block_permissions(bper_master)

        # 1. Owner can always delete a private block, even if i am not paying
        ensure = Security("goku", self.store)
        self._subscribe("goku", "enterprise_275_50_x")
        ensure.check_delete_block(brl)

        self._subscribe("freezer", "free")
        ensure.check_delete_block(brl)

        # 2. Other user can't delete block
        ensure = Security("freezer", self.store)
        self._subscribe("freezer", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_delete_block, brl)

        # 3. A user with read and write permissions cant delete
        ensure = Security("bulma", self.store)
        bper = ElementPermissions(brl, private=True)
        bper.write.grant("bulma")
        bper.read.grant("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_delete_block, brl)

        # 3. But an admin user can delete it
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_delete_block(brl)

    def test_create_block(self):
        brl = BRLBlock("goku/goku/block/master")

        # Always can make a block if its public
        ensure = Security("goku", self.store)
        self._subscribe("goku", "free")
        ensure.check_create_block(brl.owner, private=False)

        # Only can make a private block if subscription is ok
        self.assertRaises(ForbiddenException, ensure.check_create_block, brl.owner, private=True)
        self._subscribe("goku", "enterprise_275_50_x")
        ensure.check_create_block(brl.owner, private=True)

        # Other user can create a block in my namespace if its an admin, not write and read is enought
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_create_block, brl.owner, private=True)

        bper = ElementPermissions(brl.owner, private=True)
        bper.write.grant("bulma")
        bper.read.grant("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_create_block, brl.owner, private=True)

        # 3. But an admin user can delete it
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_create_block(brl.owner, private=True)
        ensure.check_create_block(brl.owner, private=False)

    def test_check_publish_block(self):
        # 1. Onwer can write the block if its private
        brl = BRLBlock("goku/goku/block/master")
        self._add_block_to_user("goku", brl, True)

        ensure = Security("goku", self.store)
        self._subscribe("goku", "enterprise_275_50_x")

        pack = PublishRequest(BlockVersion(brl, -1))
        pack.cells.append(SimpleCell('user/block/r1.h'))
        pack.contents['r1.h'] = Content(id_=None, load=Blob('hola'))
        pack.versiontag = 'mytag'

        ensure.check_publish_block(brl, pack)

        # If the owner is not paying he can't write
        ensure = Security("goku", self.store)
        self._subscribe("goku", "free")
        self.assertRaises(ForbiddenException, ensure.check_publish_block, brl, pack)
        self._subscribe("goku", "enterprise_275_50_x")

        # 1b. But other not granted user can't write
        ensure = Security("freezer", self.store)
        self._subscribe("freezer", "enterprise_275_50_x")
        self.assertRaises(ForbiddenException, ensure.check_publish_block, brl, pack)

        # 2. If bulma is granted as administrator or write he can write
        ensure = Security("bulma", self.store)
        self._subscribe("bulma", "enterprise_275_50_x")
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)
        ensure.check_publish_block(brl, pack)
        goku.administrators.revoke("bulma")
        self.store.update_user(goku)
        self.assertRaises(ForbiddenException, ensure.check_publish_block, brl, pack)

        bper = ElementPermissions(brl, private=True)
        bper.write.grant("bulma")
        self.store.upsert_block_permissions(bper)
        ensure.check_publish_block(brl, pack)
        bper.write.remove("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_publish_block, brl, pack)

        # 3. If we give read permissions only, user cant write
        bper = ElementPermissions(brl, private=True)
        bper.read.grant("bulma")
        self.store.upsert_block_permissions(bper)
        self.assertRaises(ForbiddenException, ensure.check_publish_block, brl, pack)

    def test_update_user(self):
        # Can do it himself and their administrators

        ensure = Security("goku", self.store)
        self._subscribe("goku", "enterprise_275_50_x")
        ensure.check_update_user("goku")

        self._subscribe("goku", "free")
        ensure.check_update_user("goku")

        # Other admin-granted user can't do it
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)

        ensure = Security("bulma", self.store)
        ensure.check_update_user("goku")

    def _subscribe(self, brl_user, plan_id):
        sub = self.store.read_user_subscription(brl_user)
        sub.ID = brl_user
        sub.plan_id = plan_id
        self.store.update_user_subscription(sub)
        return sub

    def _add_block_to_user(self, brl_user, brl_block, private):
        brl_block = BRLBlock(brl_block)
        user = self.store.read_user(brl_user)
        user.add_block(brl_block)
        self.store.update_user(user)

        bper_master = ElementPermissions(brl_block, private)
        self.store.upsert_block_permissions(bper_master)

    def test_subscription_limits(self):

        # Create users for test
        self.store.create_user(User("cooper"))
        self.store.create_user(User("bob"))
        self.store.create_user(User("lady_lug"))

        # Coop has a private block and a public block
        public_brl = BRLBlock("cooper/cooper/public_block/master")
        private_brl = BRLBlock("cooper/cooper/private_block/master")
        self._add_block_to_user("cooper", public_brl, False)
        self._add_block_to_user("cooper", private_brl, True)

        # 1 contributor and unlimited private blocks
        self._subscribe("cooper", "personal_7_1_x")

        # Add an administrator
        ensure = Security("cooper", self.store)
        ensure.check_grant_administrator_for("cooper", "bob")
        cooper = self.store.read_user("cooper")
        cooper.administrators.grant("bob")
        self.store.update_user(cooper)

        # Try to add another one, it must fail
        self.assertRaises(PlanUpgradeNeeded,
                          ensure.check_grant_administrator_for,
                          "cooper", "lady_lug")

        # Try to add write permissions to a public block. Its ok
        ensure.check_grant_read_or_write_permissions_to("lady_lug", public_brl)

        # Try to add write permissions to a private block, but a bob (already admin)
        ensure.check_grant_read_or_write_permissions_to("bob", private_brl)

        # Try to add write permissions to a private block. It must fail
        self.assertRaises(PlanUpgradeNeeded,
                          ensure.check_grant_read_or_write_permissions_to,
                          "lady_lug", private_brl)

        # Remove Adminsitrator, try to add write permissions in a private block. Its ok
        cooper = self.store.read_user("cooper")
        cooper.administrators.revoke("bob")
        self.store.update_user(cooper)
        ensure.check_grant_read_or_write_permissions_to("lady_lug", private_brl)
        cooper.administrators.grant("lady_lug")
        self.store.update_user(cooper)

        # Subscribe to a bigger plan and check limits
        self._subscribe("cooper", "startup_35_5_x")
        # Add 4 more
        for tmp in xrange(4):
            new_user = BRLUser("user%s" % tmp)
            ensure.check_grant_read_or_write_permissions_to(new_user, private_brl)
            bper = self.store.read_block_permissions(private_brl)
            bper.write.grant(new_user)
            self.store.upsert_block_permissions(bper)

        # The sixth must fail
        self.assertRaises(PlanUpgradeNeeded,
                          ensure.check_grant_read_or_write_permissions_to,
                          "new_user", private_brl)

        # unless user is already a contributor
        ensure.check_grant_read_or_write_permissions_to("lady_lug", private_brl)

    def test_change_subscription(self):
        # Create users for test
        self.store.create_user(User("cooper"))
        ensure = Security("cooper", self.store)
        self._subscribe("cooper", "startup_35_5_x")

        # Coop has a private block
        private_brl = BRLBlock("cooper/cooper/private_block/master")
        self._add_block_to_user("cooper", private_brl, True)

        for tmp in xrange(4):
            new_user = BRLUser("user%s" % tmp)
            ensure.check_grant_read_or_write_permissions_to(new_user, private_brl)
            bper = self.store.read_block_permissions(private_brl)
            bper.write.grant(new_user)
            self.store.upsert_block_permissions(bper)

        # Try to downgrade to personal plan
        with self.assertRaisesRegexp(ForbiddenException, "You are currently using 4 users, "
                                                         "reduce to 1 before plan downgrade"):
            ensure.check_can_change_current_subscription("cooper", "personal_7_1_x")

        # Remove collaborators to 1
        for tmp in xrange(3):
            new_user = BRLUser("user%s" % tmp)
            ensure.check_grant_read_or_write_permissions_to(new_user, private_brl)
            bper = self.store.read_block_permissions(private_brl)
            bper.write.revoke(new_user)
            self.store.upsert_block_permissions(bper)

        # Try to downgrade to personal plan
        ensure.check_can_change_current_subscription("cooper", "personal_7_1_x")

        # Try to downgrade to free plan
        with self.assertRaisesRegexp(ForbiddenException, "You are currently using 1 users, "
                                                         "reduce to 0 before plan downgrade"):
            ensure.check_can_change_current_subscription("cooper", "free")

        # Remove last collaborator
        bper = self.store.read_block_permissions(private_brl)
        bper.write.revoke("user3")
        self.store.upsert_block_permissions(bper)

        with self.assertRaisesRegexp(ForbiddenException, "You have 1 private blocks, "
                                                         "reduce it to 0 before plan downgrade"):
            ensure.check_can_change_current_subscription("cooper", "free")

    def test_check_read_user_subscription(self):
        # Can do it himself (always, event not paying) and not their administrators
        ensure = Security("goku", self.store)
        self._subscribe("goku", "enterprise_275_50_x")
        ensure.check_read_user_subscription("goku")

        self._subscribe("goku", "free")
        ensure.check_read_user_subscription("goku")

        # Other admin-granted  user cant do it
        goku = self.store.read_user("goku")
        goku.administrators.grant("bulma")
        self.store.update_user(goku)

        ensure = Security("bulma", self.store)
        ensure.check_read_user_subscription("goku")
