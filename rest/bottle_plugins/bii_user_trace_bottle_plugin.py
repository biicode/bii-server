from biicode.common.utils.bii_logging import logger
from biicode.server.rest.bottle_plugins.util import get_user_ip
from biicode.server.background.model.user_trace import UserTracedAction
from biicode.server.conf import (BII_MIXPANEL_TOKEN, BII_API_MIXPANEL_EVENT_NAME,
                                 BII_GA_API_KEY, BII_AES_SECRET_KEY)
from bottle import request
from biicode.server.utils.encryption import AESEncryption
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.publish.publish_request import PublishRequest
from biicode.server.background.enqueuer import (register_publish,
                                                register_get_version_delta_info,
                                                register_user_action)


class BiiUserTraceBottlePlugin(object):
    ''' The BiiUserTraceBottlePlugin plugin enqueue user accesses to rest api'''

    api = 2
    async_process = True  # Enqueue in redis to process in background

    def apply(self, callback, context):  # @UnusedVariable
        '''Apply plugin'''
        def wrapper(*args, **kwargs):
            '''Look at request method we are processing and queue'''
            action_name = str(callback.__name__)
            description = ""
            # We store the bson data in description, amount of data is free in heroku addon!
            if action_name != "ping":  # only for monitoring alive
                client_user = request.headers.get('X-Client-Id', None)
                auth_user = kwargs.get("auth_user", None)
                client_token = request.headers.get('X-Client-Anonymous-Id', None)

                _trace_mixpanel(action_name, auth_user, client_user, client_token, kwargs)

                description = _get_action_label(action_name, kwargs)
                _trace_user_action(action_name, auth_user, client_user, client_token, description,
                                   self.async_process)

                _trace_ga(action_name, auth_user, client_user, client_token, description)

            rv = callback(*args, **kwargs)  # kwargs has :xxx variables from url

            # Once the action was succeed, lets check achievements
            # (if didnt succeed an exception was raised)
            if action_name != "ping":  # only for monitoring alive
                _trace_achievement_action(action_name, description, auth_user or client_user,
                                          self.async_process)
            return rv

        return wrapper


def _trace_achievement_action(action_name, description, username, async_process):
    try:
        if username:
            if action_name == "publish":  # Uses publish
                register_publish(username, BlockVersion.loads(description),
                                 async_process=async_process)
            elif action_name == "get_version_delta_info":  # User uses biicode
                register_get_version_delta_info(username, async_process=async_process)
    except Exception as e:
        logger.warning("Error sending to action to achievement: %s" % e)


def _trace_user_action(action_name, auth_user, client_user, client_token, description, async_process):
    ip_address = get_user_ip()
    try:
        auth_user = auth_user or client_user or "UNKNOWN"
        action = UserTracedAction("REST", action_name, ip_address, auth_user,
                                  anonymous_user_token=client_token,
                                  description=description)
        register_user_action(action, async_process=async_process)
    except Exception as e:
        logger.warning("Error saving user trace: %s" % e)


def _trace_mixpanel(action_name, auth_user, client_user, client_token, kwargs):
    from mixpanel import Mixpanel
    from mixpanel_async import AsyncBufferedConsumer

    some_user_id = auth_user or client_user or client_token
    try:
        if action_name in ["get_server_info", "publish"]:
            mp = Mixpanel(BII_MIXPANEL_TOKEN, consumer=AsyncBufferedConsumer())
            properties = {'action': action_name, 'anonymous': (some_user_id == client_token)}
            if action_name == "get_server_info":
                properties["os"] = kwargs["bson_data"]["data"][0]["family"]
                properties["biicode_version"] = kwargs["bson_data"]["data"][1]
            mp.track(some_user_id, BII_API_MIXPANEL_EVENT_NAME, properties)
    except Exception as e:
        logger.warning("Error sending action to mixpanel: %s" % e)


def _trace_ga(action_name,  auth_user, client_user, client_token, label):
    from google_measurement_protocol import Event, report
    try:
        username = auth_user or client_user or client_token
        logger.debug("Auth user / client_user: %s/%s/%s" % (auth_user, client_user, client_token))
        logger.debug("Enter analytics with params: %s, %s, %s" % (action_name, username, label))
        aes_manager = AESEncryption(BII_AES_SECRET_KEY)
        client_id = aes_manager.encrypt(username)
        logger.debug("Client id encoded: %s" % str(client_id))
        event = Event('bii_api_call', action_name, label)

        ret = report(BII_GA_API_KEY, client_id, event)
        if ret[0].status_code == 200:
            logger.debug("ANALYTICS: Logged: %s to google analytics"
                         " for visitor %s - %s" % (action_name, username, client_id))
        else:
            logger.debug("Error logging to analytics: %s " % (ret[0].reason))
    except Exception as exc:
        logger.warning("Error sending to action to ga: %s" % (exc))


def _get_action_label(action_name, kwargs):
    """For use a third dimension in Ga"""
    try:
        block_version_from_kwargs = lambda kwargs: str(BlockVersion(
                                                       BRLBlock("%s/%s/%s" % (kwargs["owner_name"],
                                                                kwargs["block_name"],
                                                                kwargs["branch_name"])),
                                                                kwargs["version"]))
        if action_name == "get_block_info":
            return str(BRLBlock("%s/%s/%s" % (kwargs["owner_name"],
                                              kwargs["block_name"],
                                              kwargs["branch_name"])))
        elif action_name == "get_version_delta_info":
            return block_version_from_kwargs(kwargs)
        elif action_name == "get_cells_snapshot":
            return str(BlockVersion.deserialize(kwargs["bson_data"]["data"]))
        elif action_name == "get_dep_table":
            return block_version_from_kwargs(kwargs)
        elif action_name == "get_published_resources":
            return ",".join([str(BlockVersion.deserialize(elem[0]))
                             for elem in kwargs["bson_data"]["data"]])
        elif action_name == "publish":
            return str(BlockVersion.deserialize(kwargs["bson_data"]["data"]
                                                [PublishRequest.SERIAL_TRACKED_KEY]))
        elif action_name == "get_renames":
            return ", ".join([str(BlockVersion.deserialize(elem))
                             for elem in kwargs["bson_data"]["data"]])
        else:
            return ""
    except Exception as e:
        logger.error("Error getting label for GA in bii_user_trace %s" % str(e))
        return ""
