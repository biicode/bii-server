from biicode.common.exception import NotInStoreException, ForbiddenException,\
    NotFoundException
from biicode.server.model.payment.user_subscription import CURRENT_PLANS


class PlanUpgradeNeeded(ForbiddenException):
    '''Exception for trying to adding a new contributor
    if the plan don't allow more contribution or private block'''
    pass


class PlanDowngradeNotAllowed(ForbiddenException):
    '''Exception for trying to adding a new contributor
    if the plan don't allow more contribution or private block'''
    pass


class SubscriptionError(ForbiddenException):
    '''Not current subscription'''
    pass


class Security(object):
    '''define authorized methods'''

    def __init__(self, auth_user, store):
        """Auth user is the user doing the action, the user authenticated"""
        self.auth_user = auth_user
        self._store = store

    # -------------- GENERIC CHECKS -------------#

    def check_act_as_admin_of(self, brl_user):
        if self.auth_user != brl_user and self._can_act_as_admin_of(brl_user) is not True:
            raise ForbiddenException("Permission denied: Updating user %s" % brl_user)
        return

    check_read_user_subscription = check_act_as_admin_of
    check_update_card = check_act_as_admin_of
    check_handle_coupons = check_act_as_admin_of

    def check_are_own_user(self, brl_user):
        """Auth user can read brl_user subscription??"""
        if brl_user != self.auth_user:
            raise ForbiddenException("Permission denied")
        return

    def check_can_change_current_subscription(self, brl_user, plan_id):
        self.check_act_as_admin_of(brl_user)
        # Look if its a downgrade and we the destination plan
        # fits our current contributors and private blocks

        # Check destination plan is active
        dest_plan = CURRENT_PLANS[plan_id]
        if not dest_plan["active"]:
            raise ForbiddenException("Plan is no longer available")

        users, num_private_blocks = self._get_subscription_utilisation_status(brl_user)
        if dest_plan["num_users"] != -1:  # No unlimited
            if len(users) > dest_plan["num_users"]:
                raise PlanDowngradeNotAllowed("You are currently using %d users, "
                                              "reduce to %d before plan downgrade" %
                                              (len(users), dest_plan["num_users"]))

        if dest_plan["num_private_blocks"] != -1:  # No unlimited
            if num_private_blocks > dest_plan["num_private_blocks"]:
                raise PlanDowngradeNotAllowed("You have %d private blocks, "
                                              "reduce it to %d before plan downgrade" %
                                              (num_private_blocks, dest_plan["num_private_blocks"]))

    def check_subscription_limit_reached(self, brl_user, brl_new_user=None):

        contributors, num_private_blocks = self._get_subscription_utilisation_status(brl_user)
        user_subscription = self._store.read_user_subscription(brl_user)
        print user_subscription.max_users
        if brl_new_user:
            contributors.add(brl_new_user)

        # Check contributors
        if len(contributors) > user_subscription.max_users:
            more = " more" if user_subscription.max_users > 0 else ""
            raise PlanUpgradeNeeded("Upgrade plan to get%s users" % more)

        # Check num private blocks
        if user_subscription.max_private_blocks != -1:  # Unlimited
            if num_private_blocks > user_subscription.max_private_blocks:
                self.raise_upgrade_blocks(user_subscription)

    def raise_upgrade_blocks(self, user_subscription):
            more = " more" if user_subscription.max_private_blocks > 0 else ""
            raise PlanUpgradeNeeded("Upgrade plan to get%s private blocks" % more)

    # -------------- USER METHODS -------------- #

    check_update_user = check_act_as_admin_of
    check_change_password = check_act_as_admin_of
    check_read_user_permissions = check_act_as_admin_of

    def check_grant_administrator_for(self, brl_user, brl_new_user):
        self.check_act_as_admin_of(brl_user)
        self.check_subscription_limit_reached(brl_user, brl_new_user)

    def check_revoke_administrator_for(self, brl_user):
        return self.check_act_as_admin_of(brl_user)

    def check_handle_block_permissions(self, brl_block):
        self.check_act_as_admin_of(brl_block.owner)
        # Read if block is public
        block_access = self._store.read_block_permissions(brl_block)
        if block_access.is_private:
            # Check limits are ok if its free, can handle block permissions
            self.check_subscription_limit_reached(brl_block.owner)

    def check_grant_read_or_write_permissions_to(self, brl_new_user, brl_block):
        self.check_act_as_admin_of(brl_block.owner)

        # Read if block is public
        block_access = self._store.read_block_permissions(brl_block)
        if block_access.is_private:
            # Check if can add one more contributor (no more private blocks)
            self.check_subscription_limit_reached(brl_block.owner, brl_new_user)

    def check_revoke_read_or_write_permissions_to(self, brl_block):
        self.check_act_as_admin_of(brl_block.owner)

    # -------------- BLOCK METHODS -------------- #

    def check_create_block(self, brl_user, private=False):
        # Avoid Mocks to return Mock, so comparing with True
        self.check_act_as_admin_of(brl_user)
        if private:
            # Check if can add one more private block (no more contributors)
            _, num_private_blocks = self._get_subscription_utilisation_status(brl_user)
            user_subscription = self._store.read_user_subscription(brl_user)
            if user_subscription.max_private_blocks != -1:  # Unlimited
                if num_private_blocks + 1 > user_subscription.max_private_blocks:
                    self.raise_upgrade_blocks(user_subscription)

    def check_make_private_a_block(self, brl_user):
        self.check_create_block(brl_user, True)

    check_make_public_a_block = check_act_as_admin_of

    def check_read_block(self, brl_block):
        block_access = self._store.read_block_permissions(brl_block)
        if block_access.is_private:
            if not self._read_granted(brl_block, block_access):
                raise ForbiddenException("Permission denied: Reading block '%s'" % (brl_block))

    def check_write_block(self, brl_block):
        try:
            block_access = self._store.read_block_permissions(brl_block)
        except NotFoundException:
            return self.check_create_block(brl_block.owner, False)

        # If block is private, check auth_user can read it and owner is paying
        if block_access.is_private:
            # Check limits are ok, If its free will raise
            self.check_subscription_limit_reached(brl_block.owner)

        # Check if auth_user has write permissions
        if self._can_act_as_admin_of(brl_block.owner) is not True:
            if not block_access.write.is_granted(self.auth_user):
                raise ForbiddenException("Permission denied: Writing block '%s'" % brl_block)

    # Check Publish
    def check_publish_block(self, brl_block, publish_request):
        self.check_write_block(brl_block)
        user = self._store.read_user(publish_request.parent.block.owner)
        if user.blocks_bytes + publish_request.bytes > user.max_workspace_size:
            raise ForbiddenException("Workspace max size reached please contact us")

    # Delete if auth_user is an admin
    def check_delete_block(self, brl_block):
        self.check_act_as_admin_of(brl_block.owner)

    def check_read_blocks_permissions(self, brl_block):
        self.check_act_as_admin_of(brl_block.owner)

    # ############ AUX METHODS #################

    def is_private(self, brl_block):
        """Block is private?"""
        return self._store.read_block_permissions(brl_block).is_private

    def _can_act_as_admin_of(self, brl_user_owner):
        """Check if auth_user can act as block owner"""
        if not self.auth_user:
            return False  # Anonymous

        if brl_user_owner == self.auth_user:
            return True
        try:
            admins = self._store.read_user(brl_user_owner).administrators
        except NotInStoreException:
            return False
        return admins.is_granted(self.auth_user)

    def _get_subscription_utilisation_status(self, brl_user_owner):
        """Returns a tuple with a set with users, and num_private_blocks"""
        # Reads subscription and check limits
        admins = set(self._store.read_user(brl_user_owner).administrators)

        # Iterate user blocks and read the distinct users granted for read and write
        users_granted = set([])
        user = self._store.read_user(brl_user_owner)
        num_private_blocks = 0
        for brl_block in user.blocks.iterkeys():
            perms = self._store.read_block_permissions(brl_block)
            if perms.is_private:  # Only compute for private blocks
                num_private_blocks += 1
                users_granted |= perms.write | perms.read

        return admins.union(users_granted), num_private_blocks

    def _read_granted(self, brl_block, block_access):
        """ self.auth_user is granted to read brl_block?"""
        return (block_access.write.is_granted(self.auth_user) or
                block_access.read.is_granted(self.auth_user) or
                self._can_act_as_admin_of(brl_block.owner))
