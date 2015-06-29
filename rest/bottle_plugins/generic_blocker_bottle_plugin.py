from bottle import HTTPResponse
from biicode.common.utils.bii_logging import logger
import time
from collections import namedtuple
from biicode.server.rest.bottle_plugins.util import get_user_ip


class BlockerInformationPair(namedtuple('BlockerInformationPair',
                                         ['counter', 'time'])):
    '''Simple tuple pair for store counter and time'''
    pass


def default_banned_http_response():
    '''Response for banned requests'''
    return HTTPResponse("'Banned'",
                        "401 Unauthorized",
                        {"WWW-Authenticate": 'Basic realm="Login Required"'})


def _reset_info():
    '''Resets info pair'''
    return BlockerInformationPair(0, time.time())


def _parse(value):
    '''Parse memory info about block. its "counter*time"'''
    if value is None:
        return _reset_info()
    tmp = value.split("*")
    return BlockerInformationPair(int(tmp[0]), float(tmp[1]))


class GenericBlockerBottlePlugin(object):
    ''' The GenericBlockerBottlePLugin plugin ban <bantime>
     time with an not implemented condition'''

    api = 2

    def __init__(self,
                 cache,
                 delta,
                 max_events,
                 bantime,
                 callback_ip_banned=None,
                 banned_http_response=None):
        '''callback_ip_banned only called when ban period starts.
         Ideal for admin notifications'''

        self.cache = cache
        self.delta = delta
        self.max_events = max_events
        self.bantime = bantime
        self.callback_ip_banned = callback_ip_banned
        if not banned_http_response:
            self.banned_http_response = default_banned_http_response()
        else:
            self.banned_http_response = banned_http_response

    def setup(self, app):
        pass

    def apply(self, callback, context):
        '''apply generic method'''
        raise NotImplementedError("Error, implement apply in subclasses")

    def __notify_ip_banned(self, ip_address, counter, the_time):
        '''Invoke callback for banned'''
        if self.callback_ip_banned is not None and hasattr(self.callback_ip_banned, '__call__'):
            self.callback_ip_banned(ip_address, counter, the_time)

    def _check_banned(self):
        '''Check if the ip is banned'''
        ip_address = get_user_ip()
        info = self._read_info(ip_address)
        if self._is_banned(info) and not self._ban_expired(info):
            logger.error(" BANNED IP BLOCKED! " + str(ip_address)
                         + " Count: " + str(info.counter)
                         + " Time left: " + str(self._ban_time_left(info)) + " s.")
            raise self.banned_http_response
        elif self._is_banned(info) and self._ban_expired(info):
            info = _reset_info()
        logger.debug("IP: %s, Time: %s Count: %s" % (ip_address, info.time, info.counter))
        return info, ip_address

    def increment_event_counter(self, info, ip_address):
        '''Increments event counter and check for banned or reset by time'''
        try:
            if not self._count_expired(info):  # Not expired counter
                counter = info.counter + 1
                if counter >= self.max_events:
                    logger.error("BEGINS BANNED IP! " + ip_address)
                    now_time = time.time()  # Now begins banned time
                    self.__notify_ip_banned(ip_address, counter, now_time)
                else:
                    now_time = info.time
                info = BlockerInformationPair(counter, now_time)
            else:
                info = BlockerInformationPair(1, time.time())
            self._set_info(ip_address, info)
        except Exception as exc:
            logger.error("Error increment_event_counter from memcache: %s" % str(exc))

    def _is_banned(self, value):
        '''If the counter is greater than max allowed events, is banned'''
        return value.counter >= self.max_events

    def _ban_expired(self, value):
        '''Tell us if ban has been expired'''
        return value.time + self.bantime.total_seconds() < time.time()

    def _ban_time_left(self, value):
        '''Ban time left'''
        return (time.time() - (value.time + self.bantime.total_seconds()))

    def _count_expired(self, value):
        '''have passed the control time?'''
        return value.time + self.delta.total_seconds() < time.time()

    def _read_info(self, ip_address):
        '''Reads block info for an IP address'''
        return _parse(self.cache.get(self.__class__.construct_key(ip_address)))

    def delete_info(self, ip_address):
        '''Deletes info for an IP address'''
        try:
            return self.cache.delete(self.__class__.construct_key(ip_address))
        except Exception as exc:
            logger.error("Error deleting from memcache: %s" % str(exc))

    def _set_info(self, ip_address, info):
        '''Sets info for an IP address'''
        self.cache.set(self.__class__.construct_key(ip_address), "%s*%s" % (info.counter, time.time()))

    def ip_count(self, ip_address):
        '''Reads count for an ip'''
        return self._read_info(ip_address).counter

    @property
    def name(self):
        '''The plugin subclass must have a name'''
        raise NotImplementedError("Implement in block plugin subclass")

    @classmethod
    def construct_key(cls, ip_address):
        '''Construct key for the memory'''
        return "%s_%s" % (cls.name, ip_address)

    @classmethod
    def delete_memory_for(cls, cache, ip_address):
        '''Deletes memory entry for ip'''
        return cache.delete(cls.construct_key(ip_address))
