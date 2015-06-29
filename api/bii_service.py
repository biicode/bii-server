from biicode.common.api.biiapi import BiiAPI

############# Functional Collaborators #############################
from biicode.server.publish.publish_service import PublishService
from biicode.common.exception import (ForbiddenException, NotFoundException, NotInStoreException,
                                      NotActivatedUser, BiiRequestErrorException)
from biicode.common.model.server_info import ServerInfo
from biicode.server.authorize import Security
from biicode.server.find.finder_service import FindService
from biicode.server.conf import (BII_LAST_COMPATIBLE_CLIENT)
from biicode.server.store.mem_server_store import MemServerStore
from biicode.common.diffmerge.compare import compare_remote_versions
from biicode.server.user.user_service import UserService
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.server.reference_translator.reference_translator_service import ReferenceTranslatorService


# TODO: BiiService methods must capture all kind of exceptions and raise only BiiServiceException
# and subclasses. This kind of exception allow pass messages (ex.biiresponse) to final user with
# useful information about command exit, like no permissions, no-updated block, not-updated hive...
# If other kind of exception is raised, final user will only see a generic error:
# "An unexpected error has occurred in Bii service and has been reported. We hope to fix it as
# soon as possible"

class BiiService(BiiAPI):
    '''Realization of the BiiAPI, the main entry point for functionality for server remote calls'''

    def __init__(self, store, auth_user):
        '''param store: an instance of GenericServerStore, could be in memory for testing or
        MongoStore.
        param auth_user: the user invoking this service, must be prior authenticated by app'''
        self._store = store
        self._auth_user = auth_user
        self.security = Security(self._auth_user, self._store)

    def get_server_info(self):
        ''' Gets the server info'''
        from biicode.server.conf import BII_DOWNLOAD_URL
        from biicode.server.conf import BII_GREET_MSG
        si = ServerInfo(message=BII_GREET_MSG)
        si.last_compatible = BII_LAST_COMPATIBLE_CLIENT
        si.download_url = BII_DOWNLOAD_URL
        return si

    def publish(self, publish_request):
        ''' Publish in bii server'''
        p = PublishService(self._store, self._auth_user)
        return p.publish(publish_request)

    def get_block_info(self, brl_block):
        ''' Read the block and get a BlockInfo object'''
        p = PublishService(self._store, self._auth_user)
        return p.get_block_info(brl_block)

    def get_version_delta_info(self, block_version):
        """ Read the delta info of a given block version
        Raises: NotFoundException if version does not exist or is incongruent
        """
        assert block_version.time is not None
        try:
            # FIXME: Optimize, reading all block only for get last version
            self.security.check_read_block(block_version.block)
            block = self._store.read_block(block_version.block)
            if block_version.time > -1:
                return block.deltas[block_version.time]
            else:
                return None
        except NotInStoreException:
            raise NotFoundException("Block %s not found!" % block_version.block.to_pretty())
        except IndexError:
            raise NotFoundException("Block version %s not found!" % str(block_version))

    def get_version_by_tag(self, brl_block, version_tag):
        """Given a BlockVersion that has a tag but not a time returns a complete BlockVersion"""
        assert version_tag is not None
        try:
            self.security.check_read_block(brl_block)
            block = self._store.read_block(brl_block)
            for time, delta in reversed(list(enumerate(block.deltas))):
                if delta.versiontag == version_tag:
                    return BlockVersion(brl_block, time, version_tag)
            raise NotFoundException("Block version %s: @%s not found!"
                                    % (brl_block.to_pretty(), version_tag))
        except NotInStoreException:
            raise NotFoundException("Block %s not found!" % str(brl_block))

    def get_published_resources(self, reference_dict):
        ''' Get the resources by their brl'''
        r = ReferenceTranslatorService(self._store, self._auth_user)
        return r.get_published_resources(reference_dict)

    def get_dep_table(self, block_version):
        ''' Get the dependence table for this block version'''
        assert block_version.time is not None
        try:
            r = ReferenceTranslatorService(self._store, self._auth_user)
            return r.get_dep_table(block_version)
        except NotInStoreException:
            raise NotFoundException("Block %s not found!" % str(block_version.block))

    def get_cells_snapshot(self, block_version):
        ''' Gets all cell names for an specific block version '''
        assert block_version.time is not None
        brl_block = block_version.block

        try:
            self.security.check_read_block(brl_block)  # Security first, always
            block = self._store.read_block(brl_block)

            if block_version.time > len(block.deltas) - 1:
                raise NotFoundException("There is no published version %d of %s\n" %
                                        (block_version.time, block_version.block))

            tmp = block.cells.get_all_ids(block_version.time)  # Dict {cell_name: ID}
            return tmp.keys()

        except NotInStoreException:
            raise NotFoundException("Block version %s not found!\n" % str(block_version))

    def find(self, finder_request, response):
        ''' Find remote dependences '''
        store = MemServerStore(self._store)
        f = FindService(store, self._auth_user)
        return f.find(finder_request, response)

    def compute_diff(self, base_version, other_version):
        ''' Compare two versions '''
        assert base_version.time is not None
        assert other_version.time is not None
        try:
            self.security.check_read_block(base_version.block)
        except NotInStoreException:
            raise NotFoundException("Block version %s not found!\n" % str(base_version.block))

        try:
            self.security.check_read_block(other_version.block)
        except NotInStoreException:
            raise NotFoundException("Block version %s not found!\n" % str(other_version.block))

        #This biiService is only for published versions
        return compare_remote_versions(self, base_version, other_version)

    def get_renames(self, brl_block, t1, t2):
        '''Gets 2 BlockVersion ([0],[1]) in a list and returns the renames'''
        security = Security(self._auth_user, self._store)
        security.check_read_block(brl_block)
        block = self._store.read_block(brl_block)
        return block.get_renames(t1, t2)

    def require_auth(self):
        """Only for validating token
        (Used in publish manager to ensure logged user before publishing)"""
        if not self._auth_user:
            raise ForbiddenException()

    def authenticate(self, username, password):
        """ Create a "profile" object (object to encrypt) and expiration time.
        Then return the JWT token Expiration time as a UTC UNIX timestamp
        (an int) or as a datetime"""
        user_service = UserService(self._store, self._auth_user)
        try:
            _, token = user_service.authenticate(username, password)
            return token
        except NotActivatedUser:
            raise BiiRequestErrorException("User account: %s is not confirmed. Check your "
                                           "email account and follow the instructions" % username)
