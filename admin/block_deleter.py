""" So we let users really delete their things
"""
from biicode.common.exception import BiiException
from biicode.common.utils.bii_logging import logger


def block_delete(brl_block, store):
    # FIXME: No concurrency is handled now, what happens if publishing simultaneously

    try:
        block = store.read_block(brl_block)
        cell_ids, content_ids = block.all_ids()
        try:
            store.delete_published_cells(cell_ids)
        except BiiException as e:
            logger.error("Unable to delete cells %s" % e)
        try:
            store.delete_published_contents(content_ids)
        except BiiException as e:
            logger.error("Unable to delete contents %s" % e)
        store.delete_block(brl_block)
    except BiiException as e:
        logger.error("Unable to delete block or cells/contents %s" % e)
    # Deleting from user profile, should be the last thing
    # as it is required for the delete button to appear in web
    user = store.read_user(brl_block.owner)
    user.delete_block(brl_block)
    store.update_user(user)
