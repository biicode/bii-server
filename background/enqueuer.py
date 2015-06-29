import redis
from rq.queue import Queue
from urlparse import urlparse
from biicode.server.background.model.priority import Priority
from biicode.common.utils.bii_logging import logger
import traceback
from redis.exceptions import ConnectionError
from biicode.server.conf import BII_ANALYTIC_REDIS_URL, BII_LOG_TO_REDIS

redis_connection = None


def get_redis_connection(uri=None):
    uri = uri or BII_ANALYTIC_REDIS_URL

    global redis_connection

    if redis_connection:
        return redis_connection

    result = urlparse(uri)
    redis_pool = redis.ConnectionPool(host=result.hostname,
                                      max_connections=1,
                                      port=result.port, db=result.path[1:],
                                      password=result.password)
    connection = redis.Redis(connection_pool=redis_pool)
    return connection


class Enqueuer(object):
    def __init__(self, worker, async_process=True, timeout=5, priority="low", result_ttl=0, connection=None):
        """
        result_ttl=> Seconds to keep the job when finished
                     # 0 result gets deleted immediately, -1 never
        """
        self.worker = worker
        self.async_process = async_process  # If True no work is enqueued, worker method is called directly
        self.timeout = timeout
        self.priority = priority
        self.result_ttl = result_ttl
        self.connection = connection

    def enqueue_job(self, *args):
        if not BII_LOG_TO_REDIS:
            logger.debug('Skipping logging due to config')
            return
        global POOL

        if not self.async_process:  # Call the method now!
            import importlib
            module_name = ".".join(self.worker.split(".")[0:-1])
            themodule = importlib.import_module(module_name)
            call_method = getattr(themodule, self.worker.split(".")[-1])
            call_method(*args)
        try:
            priority = Priority(self.priority)
            conn = self.connection or get_redis_connection()
            q = Queue(priority, connection=conn)
            return q.enqueue_call(self.worker, args=args,
                                  timeout=self.timeout, result_ttl=self.result_ttl)
        # NOTE: this rare way to call enqueue its needed, look at the code in queue module
        except ConnectionError as e:
            logger.warn("Error connecting redis, reconnecting...")
            raise e
        except Exception as e:
            logger.warn("Error enqueuing: %s" % str(e))
            tb = traceback.format_exc()
            logger.warn(tb)
            raise e


def generic_enqueue(worker_path, parameters, timeout=60, priority="medium", async_process=True, connection=None):

    q = Enqueuer(worker_path, async_process=async_process,
                 timeout=timeout,  # Work timeout
                 priority=priority,
                 connection=connection)
    try:
        q.enqueue_job(*parameters)
    except ConnectionError as e:
        logger.error('REDIS FAIL: Redis seems to be down')
        logger.error(e)
    except Exception as e:
        logger.error("REDIS FAIL: ERROR ENQUEING"
                     " '%s' IN REDIS: %s" % (worker_path, str(e)))


def register_publish(username, block_version, async_process=True):
    """Used in background to know if a user has been reused"""
    generic_enqueue('biicode.background.worker.worker.register_publish',
                    [username, block_version],
                    async_process=async_process)


def register_signup(store, brl_user, async_process=True, connection=None):
    """Used in background to know when a user is registered"""
    method = 'biicode.background.worker.worker.register_signup'
    user = store.read_user(brl_user)
    generic_enqueue(method, [brl_user, user.email, user.full_name,
                             user.joined_date.datetime_utc, user.allow_mailing, user.staff],
                    async_process=async_process,
                    connection=connection)


def register_get_version_delta_info(auth_user, async_process=True):
    """Used in background to know if user has been used the API because
    get_version_delta_info is almost always called"""
    worker_name = 'biicode.background.worker.worker.register_get_version_delta_info'
    generic_enqueue(worker_name, [auth_user], async_process=async_process)


def register_user_action(action, async_process=True):
    worker_name = 'biicode.background.worker.worker.register_user_action'
    generic_enqueue(worker_name, [action], async_process=async_process)
