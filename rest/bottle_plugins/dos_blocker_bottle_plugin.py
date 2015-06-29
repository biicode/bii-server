from biicode.common.utils.bii_logging import logger
from biicode.server.rest.bottle_plugins.generic_blocker_bottle_plugin import GenericBlockerBottlePlugin
from bottle import HTTPResponse


class DOSBlockerBottlePlugin(GenericBlockerBottlePlugin):
    ''' The MassiveDOSBlockerBottlePlugin plugin ban <bantime> time an
        IP that makes <max_requests> requests in <delta> time interval'''

    name = 'dosloginblocker'

    def apply(self, callback, context):
        def wrapper(*args, **kwargs):
            # Checks if already banned and throws HttpResponse if banned
            info, ip = self._check_banned()
            logger.debug("IP: %s, Time: %s Attempts: %s" % (ip, info.time, info.counter))
            rv = callback(*args, **kwargs)  # kwargs has :xxx variables from url
            self.increment_event_counter(info, ip)
            return rv
        # Replace the route callback with the wrapped one.
        return wrapper

    @property
    def default_banned_http_response(self):
        return HTTPResponse(body="", status="200 OK")
