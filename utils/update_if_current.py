from biicode.common.utils.bii_logging import logger
from random import choice
import time
from biicode.server.exception import MongoNotCurrentObjectException,\
    MongoStoreException


SERIAL_TXN_COUNTER_KEY = "__c"  # Name of the transaction counter field
TXN_MAX_C = 100000  # Max 100000 updated for a specific record after an old read


def inc_txn_counter(counter):
    return (counter + 1) % TXN_MAX_C


def enable_check_for(obj):
    setattr(obj, SERIAL_TXN_COUNTER_KEY, None)  # Update if current check enabled


def safe_retry(fn):
    ''' decorator for run a function with retries if MongoNotCurrentObjectException is raised
    "max_iterations" limit the limit of attempts. Default 100
    "max_uncouple_ms" define the max miliseconds to wait for uncouple operations (random from 0 to max). Default 50
    NOTE: The model parent has to be "UpdateIfCurrentMongoObject"

    Example:

    @safe_retry
    def safety_update_user():
        r = read_user()
        r.field = value

        #Bla bla bla bla lines that do things...

        writeUser() <=== if it fails because other process has writed the object in the middle,
                         the method safety_update_user is retried "max_iterations" times waiting an random
                         time from 0 to "max_uncouple_ms" miliseconds

    '''
    def wrapped(*args, **kwargs):
        max_iterations = kwargs.pop("max_iterations", 100)  # Limit, then raise Exception
        max_uncouple_ms = kwargs.pop("max_uncouple_ms", 50)
        for i in range(max_iterations):
            try:
                logger.debug("Start try safe txn, try %s" % i)
                ret = fn(*args, **kwargs)
                logger.debug("Completed try safe txn %s" % ret)
                return ret
            except MongoNotCurrentObjectException, e:
                logger.error(str(e))
                wait_ms = choice(range(max_uncouple_ms))
                logger.debug("Waiting %s miliseconds..." % wait_ms)
                time.sleep(wait_ms / 1000)
                continue
        raise MongoStoreException("Can't accomplish the operation in max %s attempts" % (max_iterations))

    return wrapped
