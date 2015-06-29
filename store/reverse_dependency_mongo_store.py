from biicode.server.store.generic_server_store import GenericServerStore
from biicode.common.utils.bii_logging import logger
from biicode.server.model.reverse_dependency import LengthySerializedBlockVersion,\
    ReverseDependency
from biicode.common.exception import NotInStoreException


class ReverseDependencyMongoStore(object):

    REVERSE_DEPENDENCIES_ST = "reverse_dependencies"

    def __init__(self, mongo_server_store):
        self.mongo_server_store = mongo_server_store

    def read_all_blocks(self):
        dbcol = self.mongo_server_store.db[GenericServerStore.BLOCK_ST]
        cursor = dbcol.find()
        return cursor

    def upsert_reverse_dependencies(self, reverse_dependency):
        '''Upsert the reverse dependencies of a BlockVersion.
        reverse_dependency is a ReverseDependency object'''

        try:
            # Query by all block version fields (compose key) (auto ID)
            serial = reverse_dependency.serialize()
            query = reverse_dependency.version.serialize()
            self.mongo_server_store._update_collection(self.REVERSE_DEPENDENCIES_ST,
                                    query, {"$set": serial}, upsert=True, trx_record=None)

        except Exception as e:
            logger.error(e)
            raise e

    def add_reverse_dependency_to(self, block_version, new_reverse_dep):
        block_version = LengthySerializedBlockVersion(block_version.block, block_version.time)
        new_reverse_dep = LengthySerializedBlockVersion(new_reverse_dep.block,
                                                        new_reverse_dep.time)
        dbcol = self.mongo_server_store.db[self.REVERSE_DEPENDENCIES_ST]
        try:
            tmp = {ReverseDependency.SERIAL_DEPS_ON_KEY: new_reverse_dep.serialize()}
            dbcol.update(block_version.serialize(), {"$addToSet": tmp})
        except Exception as e:
            logger.error(e)
            raise e

    def read_direct_reverse_dependencies(self, block_version):
        block_version = LengthySerializedBlockVersion(block_version.block, block_version.time)

        dbcol = self.mongo_server_store.db[self.REVERSE_DEPENDENCIES_ST]
        doc = dbcol.find_one(block_version.serialize())

        if not doc:
            raise NotInStoreException("No %s found with _id = %s" % (self.REVERSE_DEPENDENCIES_ST,
                                                                     block_version))
        obj = ReverseDependency.deserialize(doc)
        return obj

    def read_direct_reverse_deps_for_brl_block(self, brl_block):
        block_version = LengthySerializedBlockVersion(brl_block, -1)
        dbcol = self.mongo_server_store.db[self.REVERSE_DEPENDENCIES_ST]
        tmp = block_version.serialize()
        # remove time key from query
        del tmp[LengthySerializedBlockVersion.SERIAL_VERSION_KEY]
        docs = dbcol.find(tmp)
        for doc in docs:
            obj = ReverseDependency.deserialize(doc)
            yield obj

    def read_direct_reverse_deps_for_owner(self, brl_user):
        dbcol = self.mongo_server_store.db[self.REVERSE_DEPENDENCIES_ST]
        # all brl_user deps (for all his blocks)
        docs = dbcol.find({LengthySerializedBlockVersion.SERIAL_OWNER_KEY: brl_user})
        for doc in docs:
            obj = ReverseDependency.deserialize(doc)
            yield obj

    # TODO: Custom query methods for reverse dependencies:
    #    1. User rating?
    #    2. Maybe aggregation framework for indirect_dependencies?
