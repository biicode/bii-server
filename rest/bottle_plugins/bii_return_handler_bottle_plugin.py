from biicode.common.utils.bii_logging import logger
from biicode.common.rest.rest_return_mapping import getHttpCodeFromException
from biicode.common.utils import serializer
import traceback
import inspect
from bottle import HTTPResponse
from biicode.common.utils.serializer import serialize
from biicode.common.api.ui import BiiResponse


class BiiReturnHandlerPlugin(object):
    ''' The BiiReturnHandlerPlugin plugin unify REST return and exception management'''

    name = 'biiresponse'
    api = 2

    def __init__(self, bsonplugin):
        self.bsonplugin = bsonplugin

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, BiiReturnHandlerPlugin):
                continue

    def apply(self, callback, context):
        '''Apply plugin'''
        def wrapper(*args, **kwargs):
            '''Capture possible exceptions to manage the return'''
            logger.info("Called: %s" % (str(callback.__name__)))
            # Add the parameter handle as a keyword argument.
            try:
                if "response" in inspect.getargspec(context.callback)[0]:
                    biiresponse = BiiResponse()
                    kwargs["response"] = biiresponse
                else:
                    biiresponse = None
                return_value = callback(*args, **kwargs)  # kwargs has :xxx variables from url
                return self.prepare_response(return_value, biiresponse)
            except HTTPResponse:
                raise  # Normal response!!!!
            except Exception as exc:
                message, code = get_message_and_code_from_exception(exc)
                return self.abort_response(code, message, biiresponse)

        # Replace the route callback with the wrapped one.
        return wrapper

    def prepare_response(self, return_value, biiresponse=None):
        result = {"return": serializer.serialize(return_value)}
        if biiresponse is not None:
            result['info'] = serialize(biiresponse)
        ret = self.bsonplugin.response_bson(result)
        return ret

    def abort_response(self, return_code, return_string, biiresponse=None):
        result = {"return": return_string}
        if biiresponse is not None:
            result['info'] = serialize(biiresponse)
        return self.bsonplugin.abort_with_bson(code=return_code, data=result)


def get_message_and_code_from_exception(exc):
    code = getHttpCodeFromException(exc)
    if code == 500:
        logger.error("%s" % str(exc))
        logger.error("%s" % traceback.format_exc())
        msg = ("An unexpected error has occurred in Bii service and has "
               "been reported. We hope to fix it as soon as possible")
        return msg, 500
    else:
        logger.info("Return code %s: %s" % (str(code), str(exc)))
        return exc.message, code
