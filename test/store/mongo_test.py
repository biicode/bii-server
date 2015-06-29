import time
import atexit
import shutil
import tempfile
import subprocess
import pymongo
import unittest
import sys
import os
from biicode.common.test.conf import BII_TEST_FOLDER
from biicode.server.store.mongo_store import MongoStore

MONGODB_TEST_PORT = 27018


class MongoTemporaryInstance(object):
    """Singleton to manage a temporary MongoDB instance

    Use this for testing purpose only. The instance is automatically destroyed
    at the end of the program.

    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            atexit.register(cls._instance.shutdown)
        return cls._instance

    def __init__(self):
        self._tmpdir = tempfile.mkdtemp(dir=BII_TEST_FOLDER)
        executable = {'darwin': '/opt/local/bin/mongod',
                      'win32': 'C:/mongodb/bin/mongod.exe'}.get(sys.platform, 'mongod')

        self._process = subprocess.Popen([executable,
                                          '--bind_ip', 'localhost',
                                          '--port', str(MONGODB_TEST_PORT),
                                          '--dbpath', self._tmpdir,
                                          '--nojournal', '--nohttpinterface',
                                          '--noauth', '--smallfiles',
                                          '--syncdelay', '0',
                                          '--maxConns', '10',
                                          '--nssize', '1',
                                          '--setParameter', 'textSearchEnabled=true'
                                          ],
                                         stderr=subprocess.STDOUT,
                                         stdout=open(os.devnull, 'wb')
                                         )
        # Instance without journaling, variable used in mongo_store to not include "j" option
        os.environ["MONGO_DISABLED_JOURNALING"] = "1"
        # XXX: wait for the instance to be ready
        #      Mongo is ready in a glance, we just wait to be able to open a
        #      Connection.
        for _ in range(6):
            time.sleep(0.5)
            try:
                # Using same connection type that real mongo server
                self._conn = MongoStore.makeConnection('localhost', MONGODB_TEST_PORT)
            except pymongo.errors.ConnectionFailure:
                continue
            else:
                break
        else:
            self.shutdown()
            assert False, 'Cannot connect to the mongodb test instance'

    @property
    def conn(self):
        return self._conn

    def shutdown(self):
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
            shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestWithMongo(unittest.TestCase):
    """TestCase with an embedded MongoDB temporary instance.

    Each test runs on a temporary instance of MongoDB. Please note that
    these tests are not thread-safe and different processes should set a
    different value for the listening port of the MongoDB instance with the
    settings `MONGODB_TEST_PORT`.

    A test can access the connection using the attribute `conn`.
    """

    _multiprocess_shared_ = True

    @classmethod
    def setUpClass(cls):
        # print 'setupClass %s' % cls.__name__
        cls.database_name = cls.__name__
        cls.tmp_mongo = MongoTemporaryInstance.get_instance()
        cls.conn = cls.tmp_mongo.conn
        cls.conn.drop_database(cls.__name__)

    @classmethod
    def tearDownClass(cls):
        # print 'tearDownClass %s' % cls.__name__
        cls.conn.drop_database(cls.__name__)
