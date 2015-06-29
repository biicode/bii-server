from biicode.server.api.jwt_manager import JWTManager
from biicode.server.conf import BII_AUTH_TOKEN_EXPIRE_MINUTES,\
    BII_JWT_SECRET_KEY
from biicode.common.utils.bii_logging import logger
import jwt


class JWTCredentialsManagerFactory(object):
    """Handles creation of JWTAccountsManager providing the right auth token"""
    @classmethod
    def new(cls, server_store):
        # Not expiring time for email confirmation
        return JWTCredentialsManager(server_store, BII_JWT_SECRET_KEY,
                                     BII_AUTH_TOKEN_EXPIRE_MINUTES)


class JWTCredentialsManager(JWTManager):
    """JWT for manage auth credentials"""

    def __init__(self, server_store, secret, expire_time):
        super(JWTCredentialsManager, self).__init__(secret, expire_time)
        self.server_store = server_store

    def get_token_for(self, brl_user):
        """Generates a token with the brl_user and additional data dict if needed"""
        user = self.server_store.read_user(brl_user)
        return JWTManager.get_token_for(self, {"user": brl_user,
                                               "password_timestamp": user.password_timestamp})

    def get_user(self, token):
        """Gets the user from credentials object. None if no credentials.
        Can raise jwt.ExpiredSignature and jwt.DecodeError"""
        profile = self.get_profile(token)
        if not profile:
            return None
        username = profile.get("user", None)
        user = self.server_store.read_user(username)
        # Timestamp must match with the stored in user, if not,
        # this token is not valid (password has been changed)
        password_timestamp = profile["password_timestamp"]
        if password_timestamp != user.password_timestamp:
            logger.debug("Timestamp doesn't match!")
            raise jwt.DecodeError("Timestamp doesn't match!")
        return username
