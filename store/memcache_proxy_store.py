from biicode.server.utils.cache import MemCachedCollection


IP_ACCESSES = "ip"


class MemCacheProxyStore(object):

    def __init__(self, store, cache_client):
        self.store = store
        self.cache_client = cache_client
        self.ip_mc_collection = MemCachedCollection(cache_client, IP_ACCESSES)

    def __getattr__(self, name):
        return getattr(self.store, name)
