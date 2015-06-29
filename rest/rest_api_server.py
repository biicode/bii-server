from biicode.server.rest import api_v1
from biicode.server.conf import BIISERVER_RUN_PORT
import bottle


class RestApiServer(object):
    server_store = None
    root_app = None

    def __init__(self, server_store):
        self.__server_store = server_store
        self.root_app = bottle.Bottle()
        api_v1.app.store = server_store
        self.root_app.mount("/v1/", api_v1.app)
        #self.__root_app.mount("/v2/",api_v2.app)

    def run(self, **kwargs):
        port = kwargs.pop("port", BIISERVER_RUN_PORT)
        debug_set = kwargs.pop("debug", False)
        bottle.Bottle.run(self.root_app, host="localhost", port=port, debug=debug_set,
                          reloader=False)
