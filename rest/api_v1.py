from biicode.server.api.bii_service import BiiService
from biicode.common.model.symbolic.reference import References
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.find.finder_request import FinderRequest
from biicode.common.utils.bii_logging import logger
from bottle import Bottle, HTTPResponse
from biicode.server.rest.bottle_plugins.dos_blocker_bottle_plugin import DOSBlockerBottlePlugin
from biicode.server.rest.bottle_plugins.bson_bottle_plugin import BSONBottlePlugin
from biicode.server.rest.bottle_plugins.massive_error_blocker_bottle_plugin import MassiveErrorBlockerBottlePlugin
from biicode.server.rest.bottle_plugins.http_basic_authentication_bottle_plugin import HttpBasicAuthenticationBottlePlugin
from biicode.server.conf import (BII_DOS_ATTACK_MAX_REQUEST, BII_DOS_ATTACK_DELTA_TIME,
                                 BII_DOS_ATTACK_BAN_TIME, BII_ERROR_ATTACK_BAN_TIME,
                                 BII_ERROR_ATTACK_MAX_ATTEMPTS, BII_ERROR_ATTACK_DELTA_TIME,
                                 BII_DOS_ATTACK_BODY_RESPONSE, BII_DOS_ATTACK_STATUS_RESPONSE,
                                 BII_ERROR_ATTACK_BODY_RESPONSE, BII_ERROR_ATTACK_STATUS_RESPONSE,
                                 BII_SSL_ENABLED, BII_ENABLED_BII_USER_TRACE)
from biicode.server.rest.bottle_plugins.non_ssl_blocker_bottle_plugin import NonSSLBlockerBottlePlugin
from biicode.server.rest.bottle_plugins.bii_return_handler_bottle_plugin import BiiReturnHandlerPlugin
from biicode.server.rest.bottle_plugins.bii_user_trace_bottle_plugin import BiiUserTraceBottlePlugin
from biicode.common.publish.publish_request import PublishRequest
from biicode.server.rest.bottle_plugins.jwt_authentication_bottle_plugin import JWTAuthenticationBottlePlugin
from biicode.server.api.jwt_credentials_manager import JWTCredentialsManagerFactory
from biicode.common.find.policy import Policy


class restV1(Bottle):

    __store = None

    def callback_ip_banned_for_DOS(self, ip, counter, time):
        logger.error("!! Banned: %s requests: %s time: %s" % (ip, counter, time))
        pass

    def callback_ip_banned_for_many_errors(self, ip, counter, time):
        logger.error("!! Banned: %s wrong logins: %s time: %s" % (ip, counter, time))
        pass

    @property
    def banned_http_response_for_DOS(self):
        return HTTPResponse(BII_DOS_ATTACK_BODY_RESPONSE,
                            BII_DOS_ATTACK_STATUS_RESPONSE
                            )

    @property
    def banned_http_response_for_many_errors(self):
        return HTTPResponse(BII_ERROR_ATTACK_BODY_RESPONSE,
                            BII_ERROR_ATTACK_STATUS_RESPONSE,
                             {"WWW-Authenticate": 'Basic realm="Login Required"'}
                            )

    @property
    def store(self):
        return self.__store

    @store.setter
    def store(self, thestore):
        self.__store = thestore
        self.install_plugins()

    def install_plugins(self):
        self.bsonplugin = BSONBottlePlugin()
        # BiiResponse plugin. All rest methods has to return
        # (data serializable | None, biiresponse) or throw BiiServiceException subclass
        logger.info("Installing BiiReturnHandlerPlugin plugin...")
        self.biiresponseplugin = BiiReturnHandlerPlugin(self.bsonplugin)
        self.install(self.biiresponseplugin)

        # Very first of all, check SSL or die
        if BII_SSL_ENABLED:  # In heroku true for all environments
            logger.info("Installing NonSSLBlockerBottlePlugin plugin...")
            nonsslblock = NonSSLBlockerBottlePlugin()
            self.install(nonsslblock)

        # First of all, check DOS attacks by IP to the API
        # Counts IP request, raise 401 if banned

        if getattr(self.store, 'ip_mc_collection', False):
            logger.info("Installing massive DOS blocker...")
            doslogin = DOSBlockerBottlePlugin(self.store.ip_mc_collection,
                                              delta=BII_DOS_ATTACK_DELTA_TIME,
                                              max_events=BII_DOS_ATTACK_MAX_REQUEST,
                                              bantime=BII_DOS_ATTACK_BAN_TIME,
                                              callback_ip_banned=self.callback_ip_banned_for_DOS,
                                              banned_http_response=self.banned_http_response_for_DOS)
            # TODO: Maybe configure a log alert (heroku) if we return 401 banned
            # to analyze the case and adjust limits?
            self.install(doslogin)

        # Second, check Http Basic auth
        logger.info("Installing http basic authentication plugin...")
        httpplugin = HttpBasicAuthenticationBottlePlugin()
        self.install(httpplugin)

        # And check auth JWT
        logger.info("Installing JWT authentication plugin...")
        jwt_manager = JWTCredentialsManagerFactory.new(self.store)
        jwt_plugin = JWTAuthenticationBottlePlugin(jwt_manager)
        self.install(jwt_plugin)

        # Third check excess of login error for an IP
        # Catch generic 401 (or 404 or other) error from authentication and stores IP,
        # raise 401 if already banned
        if getattr(self.store, 'ip_mc_collection', False):
            logger.info("Installing massive error blocker...")
            massiveerrorplugin = MassiveErrorBlockerBottlePlugin(
                                   self.store.ip_mc_collection,
                                   delta=BII_ERROR_ATTACK_DELTA_TIME,
                                   max_events=BII_ERROR_ATTACK_MAX_ATTEMPTS,
                                   bantime=BII_ERROR_ATTACK_BAN_TIME,
                                   callback_ip_banned=self.callback_ip_banned_for_many_errors,
                                   banned_http_response=self.banned_http_response_for_many_errors)
            self.install(massiveerrorplugin)

        # Last, parse BSON data
        logger.info("Installing bson plugin...")
        self.install(self.bsonplugin)

        # Logging actions
        if BII_ENABLED_BII_USER_TRACE:
            self.tracebottleplugin = BiiUserTraceBottlePlugin()
            logger.info("Installing BiiUserTraceBottlePlugin plugin...")
            self.install(self.tracebottleplugin)

app = restV1()


@app.route('/authenticate', method="GET")
def authenticate(http_basic_credentials):  # Required http_basic_authentication_bottle_plugin
    """ http_basic_credentials are not checked, only parsed from request"""
    service = BiiService(app.store, None)
    return service.authenticate(http_basic_credentials.user,
                                http_basic_credentials.password)


@app.route('/get_published_resources', method="POST")
def get_published_resources(auth_user, bson_data):
    service = BiiService(app.store, auth_user)
    references = References.deserialize(bson_data["data"])
    return service.get_published_resources(references)


@app.route('/publish', method="POST")
def publish(auth_user, bson_data):
    service = BiiService(app.store, auth_user)
    publish_request = PublishRequest.deserialize(bson_data["data"])
    return service.publish(publish_request)


@app.route('/users/:owner_name/blocks/<block_name:path>/branches/:branch_name/versions/<version:int>/block_version_table/'
           , method="GET")
def get_dep_table(auth_user, owner_name=None, block_name=None, version=None, branch_name=None):
    service = BiiService(app.store, auth_user)
    brlBlock = BRLBlock(owner_name + "/" + block_name + "/" + branch_name)
    blockversion = BlockVersion(brlBlock, version)
    return service.get_dep_table(blockversion)


@app.route('/cells_snapshot', method="POST")
def get_cells_snapshot(auth_user, bson_data):
    """Get all cell names from a specific BlockVersion"""
    service = BiiService(app.store, auth_user)
    blockversion = BlockVersion.deserialize(bson_data["data"])
    return service.get_cells_snapshot(blockversion)


@app.route('/finder_result', method="POST")
def find(auth_user, bson_data, response):
    service = BiiService(app.store, auth_user)

    # TODO: Remove this try except when next incompatible version
    try:
        finder_request = FinderRequest.deserialize(bson_data["data"])
    except KeyError:  # Keep some retro-compatibility with old policies format
        bson_data["data"][FinderRequest.SERIAL_POLICY] = Policy.default().serialize()
        finder_request = FinderRequest.deserialize(bson_data["data"])
        response.warn("Detected deprecated policy format (version < 2.7),"
                      "discarding them. Update biicode!")
    return service.find(finder_request, response)


@app.route('/diff', method="POST")
def diff(auth_user, bson_data):
    service = BiiService(app.store, auth_user)
    baseVersion = BlockVersion.deserialize(bson_data["base"])
    otherVersion = BlockVersion.deserialize(bson_data["other"])
    return service.compute_diff(baseVersion, otherVersion)


@app.route('/renames', method="POST")
def get_renames(auth_user, bson_data):
    service = BiiService(app.store, auth_user)
    # Don t want a set, want a list
    block = BRLBlock.deserialize(bson_data["block"])
    t1 = bson_data["t1"]
    t2 = bson_data["t2"]
    return service.get_renames(block, t1, t2)


@app.route('/echo', method="POST")
def test(http_basic_credentials, bson_data, response):
    """DEPRECATED, FOR ALERT USERS FOR UPDATING CLIENT. DELETE IN 2015 OR 1.1"""
    service = BiiService(app.store, http_basic_credentials.user)
    server_info = service.get_server_info()
    return server_info


@app.route('/get_server_info', method="POST")
def get_server_info(auth_user, bson_data):
    """bson_data is currently used only for log user client version etc
    in statistic trough bii_user_trace bottle plugin"""
    service = BiiService(app.store, auth_user)
    server_info = service.get_server_info()
    return  server_info


@app.route('/users/:owner_name/blocks/<block_name:path>/branches/:branch_name/info', method="GET")
def get_block_info(auth_user, owner_name=None, block_name=None, branch_name=None):
    service = BiiService(app.store, auth_user)
    brl_block = BRLBlock(owner_name + "/" + block_name + "/" + branch_name)
    return service.get_block_info(brl_block)


@app.route('/users/:owner_name/blocks/<block_name:path>/branches/:branch_name/version/<version:int>/delta_info',
           method="GET")
def get_version_delta_info(auth_user,  owner_name=None, block_name=None, branch_name=None,
                           version=None):
    brl = BRLBlock(owner_name + "/" + block_name + "/" + branch_name)
    version = BlockVersion(brl, version)
    service = BiiService(app.store, auth_user)
    return service.get_version_delta_info(version)


@app.route('/users/:owner_name/blocks/<block_name:path>/branches/:branch_name/tag/:tag',
           method="GET")
def get_version_by_tag(auth_user,  owner_name=None, block_name=None, branch_name=None, tag=None):
    brl = BRLBlock(owner_name + "/" + block_name + "/" + branch_name)
    service = BiiService(app.store, auth_user)
    return service.get_version_by_tag(brl, tag)


@app.route('/require_auth', method="GET")
def require_auth(auth_user):
    service = BiiService(app.store, auth_user)
    return service.require_auth()


@app.route('/ping', method="GET")
def ping():
    raise HTTPResponse("pong", 200)
