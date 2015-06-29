from bottle import PluginError, request, response, HTTPResponse, BottleException
import inspect
from biicode.common.utils.bson_encoding import encode_bson, decode_bson
from bson.errors import InvalidBSON
from biicode.common.utils.bii_logging import logger
from biicode.server.conf import BII_MAX_MEMORY_PER_REQUEST


class BSONBottlePluginException(BottleException):
    pass


class BSONBottlePlugin(object):
    ''' The BSONBottlePlugin plugin automatic parse BSON data if detected and
    provides some methods for bson handling'''

    name = 'bsonbottleplugin'
    api = 2

    def __init__(self, keyword='bson_data'):
        self.keyword = keyword

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if hasattr(other, "keyword"):
                if other.keyword == self.keyword:
                    raise PluginError("Found another BSONBottlePlugin plugin with "\
                    "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Test if the original callback accepts a 'self.keyword' keyword.
        args = inspect.getargspec(context.callback)[0]
        if self.keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            kwargs[self.keyword] = self._getBson()
            rv = callback(*args, **kwargs)  # kwargs has :xxx variables from url
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper

    def _getBson(self):
        ''' If the ``Content-Type`` header is ``application/bson``, this
            property holds the parsed content of the request body. Only requests
            smaller than :attr:`MEMFILE_MAX` are processed to avoid memory
            exhaustion. '''
        max_size = BII_MAX_MEMORY_PER_REQUEST
        if request.headers['Content-Type'] == 'application/bson':
            if 0 < request.content_length < max_size:
                return decode_bson(request.body.read(max_size))
            else:
                logger.error("Max size of bson for request: %i" % request.content_length)
                # DO NOT REMOVE: BODY NEEDS TO BE READED BEFORE RAISE, IT SEEMS LIKE A BOTTLE BUG
                request.body.read(0)
                raise BSONBottlePluginException("Max request size overtaken")
        else:
            raise BSONBottlePluginException("Not Bson request in a method with bson_param specified")
        return None

    def response_bson(self, data):
        self._set_bson_content_type_headers(response)
        return encode_bson(data)

    def abort_with_bson(self, code, data):
        data = encode_bson(data)
        res = HTTPResponse(status=code, body=data)
        self._set_bson_content_type_headers(res)
        #abort(code, data)
        return res

    def _set_bson_content_type_headers(self, response):
        response.set_header('Content-Type', 'application/bson')
