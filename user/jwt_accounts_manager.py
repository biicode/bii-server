from biicode.server.api.jwt_manager import JWTManager
from biicode.server.conf import BII_JWT_SECRET_MAIL_CONFIRMATION,\
    BII_JWT_SECRET_PASS_CHANGE_EXPIRE_TIME


class JWTConfirmEmailManagerFactory(object):
    """Handles creation of JWTAccountsManager providing the right auth token"""
    @classmethod
    def new(cls):
        # Not expiring time for email confirmation
        return JWTConfirmEmailManager(BII_JWT_SECRET_MAIL_CONFIRMATION,
                                      None)


class JWTPasswordResetManagerFactory(object):
    """Handles creation of JWTAccountsManager providing the right auth token"""
    @classmethod
    def new(cls):
        # Not expiring time for email confirmation
        return JWTPasswordResetManager(BII_JWT_SECRET_MAIL_CONFIRMATION,
                                       BII_JWT_SECRET_PASS_CHANGE_EXPIRE_TIME)


class JWTConfirmEmailManager(JWTManager):
    """JWT for manage tokens for reset password and confirm account"""

    def get_token_for(self, brl_user):
        """Generates a token with the brl_user"""
        return JWTManager.get_token_for(self, {"user": brl_user})

    def get_confirmed_user(self, token):
        """Gets the user from credentials object. None if no credentials.
        Can raise jwt.ExpiredSignature and jwt.DecodeError"""
        profile = self.get_profile(token)
        return None if profile is None else profile["user"]


class JWTPasswordResetManager(JWTManager):
    """JWT for manage tokens for reset password and confirm account"""

    def get_token_for(self, brl_user, password):
        """Generates a token with the brl_user"""
        return JWTManager.get_token_for(self, {"user": brl_user, "password": password})

    def get_user_and_password(self, token):
        """Gets the user from credentials object. None if no credentials.
        Can raise jwt.ExpiredSignature and jwt.DecodeError"""
        profile = self.get_profile(token)
        return None if profile is None else (profile["user"], profile["password"])
