from pymongo.mongo_client import MongoClient
from pymongo.errors import OperationFailure, DuplicateKeyError
from biicode.server.exception import (BiiStoreException, BiiPendingTransactionException,
                                     MongoNotCurrentObjectException,
                                     MongoNotFoundUpdatingException,
                                     MongoStoreException, MongoUpdateException)
from biicode.server.store.generic_server_store import GenericServerStore
from biicode.server.utils import update_if_current
import traceback
from biicode.common.utils.serializer import serialize
from biicode.common.utils.bii_logging import logger
from biicode.server.conf import BII_MONGO_URI
from biicode.common.exception import NotInStoreException, AlreadyInStoreException
from copy import copy
import os


class MongoStore(object):

    def __init__(self, connection, databasename):
        self.connection = connection

        if databasename is None:
            self.database_name = copy(BII_MONGO_URI.split("/")).pop()
        else:
            self.database_name = databasename

        #print self.database_name
        self.db = self.connection[self.database_name]

    @staticmethod
    def makeConnection(*args, **kwargs):
        ''' Makes mongo connection. Pass user, password or URI as single parameter'''
        m = MongoClient(*args, **kwargs)
        MongoStore.setWriteConcerns(m)
        return m

    @staticmethod
    def setWriteConcerns(mongoclient):
        # If True block until write operations have been committed to the journal.
        # For testing purpose, db version v2.6.7 doesn't allow this
        # configuration with running server without journaling
        if os.environ.get("MONGO_DISABLED_JOURNALING", "0") == "0":
            mongoclient.write_concern['j'] = True
        #w: (integer or string) If this is a replica set, write operations will block until they
        # have been replicated
        #to the specified number or tagged set of servers. w=<int> always includes the replica set
        #primary (eg. w=3 means write to the primary and wait until replicated to two secondaries).
        #Setting w=0 disables write acknowledgement and all other write concern options.
        mongoclient.write_concern['w'] = 1
        pass

    def read(self, object_id, collection, fields=None, deserializer=None):
        '''fields: if specified only this fields are fetched
           deserializer: if specified use this instead of generic collection deserializer
                         if False, dict is returned'''
        logger.debug("**FIND ONE: %s - %s" % (str(collection), str(object_id)))
        dbcol = self.db[collection]
        s = serialize(object_id)

        projection = dict([(name, 1) for name in fields]) if fields else None
        doc = dbcol.find_one({"_id": s}, projection)

        if not doc:
            raise NotInStoreException("No %s found with _id = %s" % (collection, object_id))

        deserializer_method = self._get_deserializer_method(deserializer, collection)
        obj = deserializer_method(doc)

        txn_k = update_if_current.SERIAL_TXN_COUNTER_KEY  # Requires update_if_current check
        if txn_k in doc and not isinstance(obj, dict):
            setattr(obj, txn_k, doc[txn_k])

        return obj

    def read_multi(self, object_ids, collection, fields=None, deserializer=None):
        '''fields: if specified only this fields are fetched
           deserializer: if specified use this instead of generic collection deserializer
                         if False, dict is returned'''
        dbcol = self.db[collection]
        ids = [a.serialize() for a in object_ids]

        projection = dict([(name, 1) for name in fields]) if fields else None

        cursor = dbcol.find({"_id": {"$in": ids}}, projection)
        des_key = self.getDeserializerMulti(collection)

        deserializer_method = self._get_deserializer_method(deserializer, collection)
        result = {des_key.deserialize(doc["_id"]): deserializer_method(doc) for doc in cursor}
        return result

    def _get_deserializer_method(self, deserializer, collection):
        if deserializer is None:
            return self.getDeserializer(collection).deserialize
        elif deserializer is False:  # Deserialize false => Not deserialize
            return lambda obj: obj
        else:
            return deserializer.deserialize

    def create(self, value, collection, enable_update_if_current=False):
        dbcol = self.db[collection]
        txn_k = update_if_current.SERIAL_TXN_COUNTER_KEY

        if enable_update_if_current:
            update_if_current.enable_check_for(value)

        serial = value.serialize()
        if hasattr(value, txn_k):
            serial[txn_k] = 0
            setattr(value, txn_k, 0)

        try:
            id_or_error = dbcol.insert(serial, getLastError=1)
            if isinstance(id_or_error, basestring) \
                and '_id' in serial and id_or_error != serial['_id']:
                raise BiiStoreException(id_or_error)
            return id_or_error
        except DuplicateKeyError as e:
            raise AlreadyInStoreException(e)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e

    def create_multi(self, values, collection, enable_update_if_current=False):
        dbcol = self.db[collection]
        txn_k = update_if_current.SERIAL_TXN_COUNTER_KEY

        serials = []
        for v in values:
            if enable_update_if_current:
                update_if_current.enable_check_for(v)
            serial = v.serialize()
            if hasattr(v, txn_k):
                serial[txn_k] = 0
                setattr(v, txn_k, 0)
            serials.append(serial)

        try:
            id_or_error = dbcol.insert(serials, getLastError=1)
            if isinstance(id_or_error, basestring) \
                and '_id' in serial and id_or_error != serial['_id']:
                raise BiiStoreException(id_or_error)
        except Exception, e:
            logger.error(traceback.format_exc())
            raise e
        return id_or_error

    def update(self, value, collection, upsert=False, is_serialized=False):
        try:
            if is_serialized:
                serial = value
            else:
                serial = value.serialize()
            query = {'_id': serial['_id']}
            txn_k = update_if_current.SERIAL_TXN_COUNTER_KEY
            trx_record = hasattr(value, txn_k)  # Requires update_if_current check

            if trx_record:
                # Query updated
                query[txn_k] = getattr(value, txn_k)
                # Update in DB the counter if its a clean object
                serial[txn_k] = update_if_current.inc_txn_counter(query[txn_k])
                # Update object in memory with new counter
                # (otherwise 2 updates for same object will fail)
                setattr(value, txn_k, serial[txn_k])

            serial.pop('_id')
            self._update_collection(collection, query, {"$set": serial}, upsert, trx_record)

        except Exception, e:
            tb = traceback.format_exc()
            logger.error(e)
            logger.error(tb)
            raise e

    def count(self, collection):
        collection = self.db[collection]
        return collection.count()

    def stats(self):
        """http://docs.mongodb.org/manual/reference/command/dbStats/"""
        return self.db.command("dbstats")

    def update_multi(self, values, collection, upsert=False, is_serialized=False):
        for value in values:
            # MongoDB update Modifies an existing document
            self.update(value, collection, upsert, is_serialized)

    def update_field(self, collection, obj_id, field_name, value):
        # TODO: Add update_if_current check?
        query = {'_id': serialize(obj_id)}
        update_st = {field_name: serialize(value)}
        return self._update_collection(collection, query, {"$set": update_st}, upsert=False,
                                       trx_record=False)

    def _update_collection(self, collection_name, query, set_statement, upsert, trx_record):
        dbcol = self.db[collection_name]
        ret = dbcol.update(query, set_statement, upsert=upsert)
        if "error" in ret and ret['error'] is not None:
            raise MongoUpdateException("Error updating object: %s, %s" % (str(ret), query))
        if "ok" in ret and ret['ok'] != 1:
            raise MongoUpdateException("Error updating object: %s, %s" % (str(ret), query))
        if trx_record and not ret['updatedExisting']:
            raise MongoNotCurrentObjectException("Object with txn counter not found!: %s" % query)
        if not upsert and not ret['updatedExisting']:
            raise MongoNotFoundUpdatingException("Object not found: %s" % query)
        # if upsert and not ret['updatedExisting']: #Nonsense, if upsert does insert instead of
        # update updatedExisting is False
        #    raise MongoUpsertException("Error upserting: %s\nRet: %s" % (query, ret))
        if "jnote" in ret:
            if ret['jnote'] == "journaling not enabled on this server":
                logger.warning("Mongo journaling not enabled in this server!!")
            else:
                logger.debug(ret['jnote'])

        return ret

    def upsert(self, value, collection, is_serialized=False):
        return self.update(value, collection, upsert=True, is_serialized=is_serialized)

    def upsert_multi(self, values, collection, is_serialized=False):
        self.update_multi(values, collection, upsert=True, is_serialized=is_serialized)

    def delete(self, value, collection):
        dbcol = self.db[collection]
        dbcol.remove({"_id": serialize(value)})

    def delete_multi(self, values, collection):
        dbcol = self.db[collection]
        serialized = [serialize(value) for value in values]
        dbcol.remove({"_id": {"$in": serialized}})

    #########################################################

    def getDeserializer(self, collection):
        raise NotImplementedError()  # Implemented in mongo_server_store

    def getDeserializerMulti(self, collection):
        raise NotImplementedError()  # Implemented in mongo_server_store

    ######################### Transactions ###########################
    def _request_transaction(self, collection, entity_name, brl):
        transaction_definition = {'_id': brl.serialize(),
                                  'state': 'initial'}
        dbcol = self.db[collection]

        try:
            id_or_error = dbcol.insert(transaction_definition, getLastError=1)
        except DuplicateKeyError:
            raise BiiPendingTransactionException('There\'s a pending transaction for %s %s'
                                                ', please retry later'
                                                % (entity_name, transaction_definition['_id']))

        if isinstance(id_or_error, basestring) \
             and id_or_error != transaction_definition['_id']:
            raise BiiPendingTransactionException('There\'s a pending transaction for %s %s'
                                                + ', please retry later'
                                                % (entity_name, transaction_definition['_id']))
        return dbcol.find_one({'_id': transaction_definition['_id'], 'state': "initial"})

    def _finish_transaction(self, collection, brl):
        dbcol = self.db[collection]
        dbcol.remove({'_id': brl.serialize(),
                      'state': {"$in": ['commited', 'canceled', 'initial']}})

    def _commit_transaction(self, collection, brl):
        dbcol = self.db[collection]
        dbcol.update({'_id': brl.serialize(), 'state': 'pending'},
                     {"$set": {'state': "commited"}})

    def _begin_transaction(self, collection, brl, backup_content):
        try:
            dbcol = self.db[collection]
            transaction_definition = {'state': 'pending'}
            transaction_definition.update(backup_content)
            dbcol.update({'_id': brl.serialize(), 'state': 'initial'},
                         {"$set": transaction_definition})
        except OperationFailure as e:
            tb = traceback.format_exc()
            logger.error(tb)
            raise MongoStoreException(e)

    def _cancel_transaction(self, collection, brl):
        dbcol = self.db[collection]
        transaction = dbcol.find_and_modify({'_id': brl.serialize()},
                                            {"$set": {'state': "canceling"}},
                                            new=True)
        return transaction

    def _finish_rollback(self, collection, brl):
        dbcol = self.db[collection]
        dbcol.update({'_id': brl.serialize(), 'state': 'canceling'},
                     {"$set": {'state': "canceled"}})

    ######################### Block Transactions ######################
    BLOCK_TRANSACTIONS = 'block_transactions'

    def requestBlockTransaction(self, block_brl):
        self._request_transaction(self.BLOCK_TRANSACTIONS, 'block', block_brl)

    def beginBlockTransaction(self, block_brl, cells, contents):
        backup_content = {'cells': [c.serialize() for c in cells],
                          'contents': [c.serialize() for c in contents]}
        self._begin_transaction(self.BLOCK_TRANSACTIONS, block_brl, backup_content)

    def rollBackBlockTransaction(self, block_brl):
        transaction = self._cancel_transaction(self.BLOCK_TRANSACTIONS, block_brl)

        ids_cells = [cell["_id"] for cell in transaction['cells']]
        self.delete_multi(ids_cells, GenericServerStore.PUBLISHED_CELL_ST)

        ids_contents = [content["_id"] for content in transaction['contents']]
        self.delete_multi(ids_contents, GenericServerStore.PUBLISHED_CONTENT_ST)

        self._finish_rollback(self.BLOCK_TRANSACTIONS, block_brl)

    def commitBlockTransaction(self, block_brl):
        self._commit_transaction(self.BLOCK_TRANSACTIONS, block_brl)

    def finishBlockTransaction(self, block_brl):
        self._finish_transaction(self.BLOCK_TRANSACTIONS, block_brl)
