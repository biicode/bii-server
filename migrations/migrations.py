from biicode.common.migrations.migration import Migration


######### DO NOT DELETE *NEVER* A CLASS FROM THIS MODULE ##############

class AddContributorsAndPermissionsToWorkspace(Migration):
    def migrate(self, *args, **kwargs):
        # Deprecated, userworkspace not exists anymore
        pass


class AddTagsToWorkspaceBlocks(Migration):

    def migrate(self, *args, **kwargs):
        # Deprecated, userworkspace not exists anymore
        pass


class EnsureUserSubscriptionCreated(Migration):

    def migrate(self, *args, **kwargs):
        # Aldready migrated
        pass


class PGUserAndWorkspaceToUser(Migration):
    def migrate(self, *args, **kwargs):
        # Aldready migrated
        pass


class ResetUserSubscription(Migration):
    '''To new model'''
    def migrate(self, *args, **kwargs):
        # Aldready migrated
        pass


class ComputeUserWorkspaceSizes(Migration):

    def migrate(self, *args, **kwargs):
        # Aldready migrated
        pass


# DO NOT DELETE **NEVER** ELEMENTS IN THIS LIST. ONLY APPEND NEW MIGRATIONS!!
SERVER_MIGRATIONS = [
    AddContributorsAndPermissionsToWorkspace(),  # Add contributors and permissions to workspace
    AddTagsToWorkspaceBlocks(),  # Add tags to workspace
    PGUserAndWorkspaceToUser(),  # Change user workspace structure for search capability
    EnsureUserSubscriptionCreated(),  # All users with empty suscription
    ResetUserSubscription(),
    ComputeUserWorkspaceSizes()  # Compute the size of contents of users
]
