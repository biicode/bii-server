from bottle import HTTPResponse, request, BaseResponse
from biicode.server.rest.bottle_plugins.generic_blocker_bottle_plugin import \
    GenericBlockerBottlePlugin


class MassiveErrorBlockerBottlePlugin(GenericBlockerBottlePlugin):
    ''' The MassiveErrorBlockerBottlePlugin plugin ban <bantime> time an
        IP that makes <attempts> wrong logins (or bad request) in <delta> time interval.

        It prevents force login or crawlers searching for non known private blocks'''

    name = 'massiveerrorblocker'

    def apply(self, callback, _):
        '''method called for wrap plugin operation'''

        def wrapper(*args, **kwargs):
            '''Wrap plugin chain. Checks if already banned and
            throws HttpResponse if banned'''
            info, ipaddress = self._check_banned()
            try:
                callbackret = callback(*args, **kwargs)
                # Not exception but prepared response
                if isinstance(callbackret, BaseResponse):
                    if callbackret.status_code >= 400 and callbackret.status_code <= 499:
                        self.increment_event_counter(info, ipaddress)
                    else:
                        if request.method != "OPTIONS":  # Not clear for an options request
                            self.delete_info(ipaddress)  # Login ok, delete info

                return callbackret
            except HTTPResponse as excp:
                if excp.status_code >= 400 and excp.status_code <= 499:
                    self.increment_event_counter(info, ipaddress)
                    raise excp
                else:
                    raise excp  # Other exception

        # Replace the route callback with the wrapped one.
        return wrapper
