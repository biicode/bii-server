from biicode.server.model.user import User
from biicode.server.model.block import Block
from biicode.common.model.content import ContentDeserializer
from biicode.common.model.cells import CellDeserializer
from biicode.common.model.id import ID
from biicode.server.store.mongo_store import MongoStore
from biicode.server.store.generic_server_store import GenericServerStore
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.server.exception import BiiPendingTransactionException
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.server.model.payment.user_subscription import UserSubscription


class MongoServerStore(MongoStore, GenericServerStore):
    deserializer = {
        GenericServerStore.PUBLISHED_CELL_ST: CellDeserializer(ID),
        GenericServerStore.PUBLISHED_CONTENT_ST: ContentDeserializer(ID),
        GenericServerStore.BLOCK_ST: Block,
        GenericServerStore.USER_ST: User,
        GenericServerStore.COUNTERS_ST: None,
        GenericServerStore.BLOCK_PERMISSIONS_ST: ElementPermissions,
        GenericServerStore.USER_SUBSCRIPTION_ST: UserSubscription
    }

    def __init__(self, connection, databasename=None):
        '''
        connection: MongoClient, can be get from MongoStore.makeConnection
        '''
        MongoStore.__init__(self, connection, databasename)

    def read_user_by_email(self, email):
        '''Reads user by email'''
        dbcol = self.db[GenericServerStore.USER_ST]
        doc = dbcol.find_one({User.SERIAL_EMAIL: email})
        return User.deserialize(doc) if doc else None

    def read_user_by_oauth_token(self, provider, token):
        '''Reads user by github or google token'''
        cols = {"google": User.SERIAL_OAUTH_GOOGLE_TOKEN,
                "github": User.SERIAL_OAUTH_GITHUB_TOKEN}
        dbcol = self.db[GenericServerStore.USER_ST]
        doc = dbcol.find_one({cols[provider]: token})
        return User.deserialize(doc) if doc else None

    def read_user_subscription_by_customer_id(self, customer_id):
        dbcol = self.db[GenericServerStore.USER_SUBSCRIPTION_ST]
        doc = dbcol.find_one({UserSubscription.SERIAL_CUSTOMER_ID_KEY: customer_id})
        return UserSubscription.deserialize(doc) if doc else None

    def exists_user_id_ignoring_case(self, brl_user):
        '''Check if user already exists with a case insensitive pattern'''
        import re
        dbcol = self.db[GenericServerStore.USER_ST]
        doc = dbcol.find_one({User.SERIAL_ID_KEY: re.compile('^' + re.escape(brl_user) + '$',
                                                             re.IGNORECASE)})
        return User.deserialize(doc) if doc else None

    def generate_user_id(self):
        counters = self.db["counters"]
        updated = counters.find_and_modify(query={'_id': 'users'},
                                update={"$inc": {'seq': 1}},
                                upsert=True,
                                new=True)
        return ID((updated['seq'], ))

    def getDeserializer(self, collection):
        '''Mapping our collections'''
        return MongoServerStore.deserializer[collection]

    def getDeserializerMulti(self, collection):  # For read_multi keys
        '''Mapping our collections'''
        return {
                GenericServerStore.PUBLISHED_CELL_ST: ID,
                GenericServerStore.PUBLISHED_CONTENT_ST: ID,
                GenericServerStore.BLOCK_ST: BRLBlock,
                GenericServerStore.BLOCK_PERMISSIONS_ST: BRLBlock,
                }[collection]

    def check_transaction(self, brl_hive):
        dbcol = self.db[MongoStore.HIVE_TRANSACTIONS]
        transaction = dbcol.find_one({'_id': str(brl_hive)})
        if transaction is not None:
            raise BiiPendingTransactionException("Cannot read hive %s, try again later"
                                                 % transaction)

    ############ Get content size ################
    def read_content_sizes(self, content_ids):
        dbcol = self.db[GenericServerStore.PUBLISHED_CONTENT_ST]
        ids = [a.serialize() for a in content_ids]
        projection = {"l.sz": 1}
        cursor = dbcol.find({"_id": {"$in": ids}}, projection)
        result = {ID.deserialize(doc["_id"]): doc["l"]["sz"] for doc in cursor}

        return result

    ########### Get published blocks info ############
    def read_published_blocks_info(self):
        """Gets the blocks brl's with the last publish date in a tuple.
        The method returns a generator, blocks can be a lot and we don't want it all in memory
        """
        dbcol = self.db[GenericServerStore.BLOCK_ST]
        brls = dbcol.find({}, {"_id": 1})  # Iterator in results
        for ret_brl_block in brls:  # Its an iterator too
            brl_block = BRLBlock(ret_brl_block["_id"])
            the_block = self.read_block(brl_block)
            last_delta = the_block.last_delta
            if last_delta:
                last_pub_date = last_delta.datetime
                yield (brl_block, last_pub_date)
