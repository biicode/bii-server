from biicode.server.model.block import Block
from biicode.common.exception import (ForbiddenException, PublishException, NotFoundException,
                                      ServerInternalErrorException, NotInStoreException,
                                      BiiRequestErrorException, BiiServiceException,
                                      AlreadyInStoreException)
from biicode.server.exception import DuplicateBlockException
from biicode.common.utils.bii_logging import logger
import traceback
from biicode.server.authorize import Security
from biicode.common.model.block_info import BlockInfo
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.version_tag import DEV


class PublishService(object):
    ''' Service for publish blocks in server.'''
    def __init__(self, store, auth_user):
        self._store = store
        self.auth_user = auth_user
        self.security = Security(self.auth_user, self._store)

    def publish(self, publish_request):
        '''Performs a publication
        TIP: If we add publish_request to transaction_definition we can easily have asynchronous
        publications

        private: Only for first publication
        '''
        from biicode.server.background.enqueuer import register_publish

        if publish_request.tag == DEV:
            if not publish_request:
                raise BiiRequestErrorException('Up to date, nothing to publish')
            if publish_request.versiontag is not None:
                raise PublishException('A DEV version cannot have tag %s' % publish_request.tag)

        assert publish_request.deptable is not None

        # by default it is public
        # TODO: BLock creation is not handled in the transaction
        target_version = publish_request.parent
        user = self._store.read_user(target_version.block.owner)
        # Look if user has the block already created, because the block
        # can exist with -1 version if it has been created in web
        if target_version.block not in user.blocks.keys():
            try:
                if target_version != publish_request.parent:  # Branching
                    user = self.create_block(target_version.block,
                                             publish_request.parent, private=False)
                else:
                    user = self.create_block(target_version.block, private=False)
            except DuplicateBlockException:
                pass  # Its ok, already created

        target_block = target_version.block
        self._store.requestBlockTransaction(target_block)
        try:
            # If we can't read the block, we can't know about his existence
            self.security.check_read_block(target_block)
            self.security.check_publish_block(target_block, publish_request)
            # biiresponse.debug('Read block "%s"' % brl_block)
            block = self._store.read_block(target_block)
            (cells, contents,
             old_cells_ids, old_content_ids) = self._in_memory_block_update(block, publish_request)
        except ForbiddenException:
            self._store.finishBlockTransaction(target_block)
            raise
        except PublishException as e:
            self._store.finishBlockTransaction(target_block)
            raise ServerInternalErrorException(e.message)
        except Exception as excp:
            logger.error("Exception in publish service!!: %s " % str(excp))
            tb = traceback.format_exc()
            logger.error(tb)
            self._store.finishBlockTransaction(target_block)
            raise ServerInternalErrorException()

        self._store.beginBlockTransaction(target_block, cells, contents)
        try:
            self._write_resources_to_db(cells, contents, old_cells_ids, old_content_ids)
            self._store.update_block(block)
            self._store.commitBlockTransaction(target_block)
            register_publish(self.auth_user, block.last_version())
            self._store.finishBlockTransaction(target_block)

            # Need to read user again, otherwise will raise MongoNotCurrentObjectException
            # because of double update of same memory object
            user = self._store.read_user(target_version.block.owner)
            user.add_block_size_bytes(target_version.block, publish_request.bytes)
            # Save user (with block bytes updated)
            self._store.update_user(user)

            return block.last_version()

        except Exception as excp:
            tb = traceback.format_exc()
            logger.debug(tb)
            self._rollback_transaction(excp, target_block)
            raise ServerInternalErrorException('Publish transaction failed. Please, retry')

    def create_block(self, brl, private=False):
        '''Creates a block in server due the brl and description'''
        self.security.check_create_block(brl.owner, private)
        user = self._store.read_user(brl.owner)
        try:
            block_id = user.add_block(brl)  # should fail if existing
        except DuplicateBlockException:
            logger.debug('Block %s already existing, not creating it' % brl)
            raise

        block = Block(block_id, brl)
        try:  # FIXME: better upsert?
            self._store.create_block(block, private)  # should fail if existing
        except AlreadyInStoreException:
            pass
        self._store.update_user(user)  # raise exception if not current

        return user

    def _rollback_transaction(self, excp, brl_block):
        '''rollback transaction for publish'''
        logger.warning(str(excp) + '\nRolling back publish transaction')
        self._store.rollBackBlockTransaction(brl_block)
        self._store.finishBlockTransaction(brl_block)

    def _write_resources_to_db(self, cells, contents, old_cells_ids, old_content_ids):
        '''Write cells and contents to db'''
        if old_cells_ids:
            self._store.delete_published_cells(old_cells_ids)
        if old_content_ids:
            self._store.delete_published_contents(old_content_ids)
        if cells:
            self._store.create_published_cells(cells)
        if contents:
            self._store.create_published_contents(contents)

    # @mongo_update_if_current_safe_retry
    # def __update_user_if_current(self, user):
    def _set_cell_roots(self, block, publish_request):
        '''Set cell root'''
        # Ensure here root assignment
        old_ids = {}
        deltas = block.deltas
        last_time = len(deltas) - 2

        for res in publish_request.cells:
            old_name = publish_request.renames.get_old_name(res.name.cell_name)
            old_id = block.cells.get_id(old_name, last_time)
            if old_id:
                old_ids[old_id] = res
            else:
                res.root = res.ID
        old_cells = self._store.read_published_cells(old_ids.keys())
        for old_id, old_cell in old_cells.iteritems():
            res = old_ids[old_id]
            res.root = old_cell.root

    def _in_memory_block_update(self, block, publish_request):
        '''Updates block in memory'''
        self.security.check_write_block(block.ID)
        cells, contents, old_cells_ids, old_content_ids = block.add_publication(publish_request,
                                                                                self.auth_user)
        self._set_cell_roots(block, publish_request)
        return cells, contents, old_cells_ids, old_content_ids

    def get_block_info(self, brl_block):
        '''Check if auth_user can publish a block version specified by parameter block_version
         Returns:
            BlockInfo
         '''

        try:
            self.security.check_read_block(brl_block)
        except NotInStoreException:
            # In this case, the block doesnt exist, but return information of -1 and permissions
            return self._get_new_block_info(brl_block)

        block_info = BlockInfo()
        try:
            self.security.check_write_block(brl_block)
            block_info.can_write = True
        except ForbiddenException:
            block_info.can_write = False

        try:
            block = self._store.read_block(brl_block)
            block_info.last_version = block.last_version()
            block_info.private = self.security.is_private(brl_block)
        except Exception as e:
            tb = traceback.format_exc()
            logger.debug(tb)
            logger.error("Something went wrong with %s" % e)
            raise BiiServiceException('Something went wrong')

        return block_info

    def _get_new_block_info(self, brl_block):
        '''
        Returns BlockInfo that new block would have if we publish it.
        Raises exception if block cannot be created for any reason
        '''
        last_version = BlockVersion(brl_block, -1)
        can_write = False
        try:
            self.security.check_create_block(brl_block.owner)
            can_write = True
        except ForbiddenException:
            can_write = False
        except NotInStoreException:
            raise NotFoundException("Block %s not found!" % brl_block.to_pretty())

        return BlockInfo(can_write=can_write, last_version=last_version)
