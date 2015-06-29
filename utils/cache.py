from biicode.common.utils.bii_logging import logger


class MemCachedCollection(object):

    def __init__(self, mc, collection_name):
        self.mc = mc
        self.collection_name = collection_name

    def get(self, key):
        key = self._construct_key(key)
        try:
            el = self.mc.get(key)
            return el
        except Exception as exc:
            return None

    def set(self, key, value, expire_seconds=0):
        key = self._construct_key(key)
        try:
            ret = self.mc.set(key, value, time=int(expire_seconds))
        except Exception as exc:
            logger.error(exc)
            return None

        return ret

    def delete(self, key):
        key = self._construct_key(key)
        return self.mc.delete(key)

    def _construct_key(self, key):
        key = self.collection_name + "@" + key
        return key
