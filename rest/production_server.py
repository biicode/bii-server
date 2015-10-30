import sys
from biicode.server.rest.rest_api_server import RestApiServer
from biicode.server.conf import BII_MONGO_URI, BII_MEMCACHE_SERVERS,\
    BII_MEMCACHE_USERNAME, BII_MEMCACHE_PASSWORD, BII_MAX_MONGO_POOL_SIZE
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.store.mongo_store import MongoStore

store = MongoServerStore(MongoStore.makeConnection(BII_MONGO_URI,
                                                   max_pool_size=BII_MAX_MONGO_POOL_SIZE))

if BII_MEMCACHE_SERVERS:
    from biicode.server.store.memcache_proxy_store import MemCacheProxyStore
    import pylibmc
    client = pylibmc.Client(servers=[BII_MEMCACHE_SERVERS],
                            username=BII_MEMCACHE_USERNAME,
                            password=BII_MEMCACHE_PASSWORD,
                            binary=True)

    proxy = MemCacheProxyStore(store, client)
else:
    proxy = store

# Run with: gunicorn -b 0.0.0.0:9000 -k gevent_pywsgi biicode.server.rest.production_server:app
ra = RestApiServer(proxy)
app = ra.root_app
