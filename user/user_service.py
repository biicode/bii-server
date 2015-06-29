from biicode.common.exception import (NotInStoreException, NotFoundException,
                                      InvalidNameException,
                                      ForbiddenException, AuthenticationException)
from biicode.server.authorize import Security
from biicode.server.model.user import User
from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.utils.bii_logging import logger
import datetime
from biicode.common.exception import NotActivatedUser
from biicode.server.user.jwt_accounts_manager import (JWTConfirmEmailManagerFactory,
                                                      JWTPasswordResetManagerFactory)
from biicode.server.api.jwt_credentials_manager import JWTCredentialsManagerFactory
from biicode.server.exception import ControledErrorException
import traceback
from biicode.server.user.oauth import OAuthService, get_oauth_service
from biicode.server.background.enqueuer import register_signup


MIN_PASSWORD_LENGTH = 6


class UserService(object):
    """Handles the registration, user profile updating, user confirmation.
    """

    def __init__(self, store, auth_user):
        self.store = store
        self.auth_user = auth_user
        self.security = Security(auth_user, store)

    def edit_user(self, brl_user):
        """Get User fields for edition"""
        self.security.check_update_user(brl_user)
        user = self.get_user(brl_user)
        user = user_to_json(user)
        return user

    def view_user(self, brl_user):
        try:
            user = self.get_user(brl_user)
        except NotInStoreException:
            raise NotFoundException("No user found with name %s" % brl_user)
        # FIXME: Can read email
        user_json = user_to_json(user)
        del user_json["visible_email"]
        del user_json["allow_mailing"]
        if not user.visible_email and brl_user != self.auth_user:
            user_json["email"] = None
        return user_json

    def get_user(self, brl_user):
        '''Retrieve user information'''
        try:
            user = self.store.read_user(brl_user)
        except NotInStoreException:
            raise NotFoundException()
        if not user.active:
            raise NotFoundException()
        # Not propagate sensible information
        user.staff = None
        user.last_api_call = None
        user.active = None
        user.confirmation_token = None
        user.joined_date = None
        user.confirmation_date = None

        auth_blocks = {}
        # Read all blocks and filter private ones
        for brl_block, block_meta in user.blocks.iteritems():
            try:
                block_access = self.store.read_block_permissions(brl_block)
                self.security.check_read_block(brl_block)
                # block_meta => ([tags], description, bytes)
                block_meta.append(block_access.is_private)
                auth_blocks[brl_block] = block_meta
            except ForbiddenException:
                pass
        user.blocks = auth_blocks

        return user

    def register(self, brl_user, email, plain_password, allow_mailing,
                 provider=None, access_token=None, invited_by=None):

        '''
        :param: user is a web_api.model.User
        '''
        # Validate password
        if len(plain_password) < MIN_PASSWORD_LENGTH:
            logger.debug("Invalid password length for %s" % email)
            raise ControledErrorException("Password length must"
                                          " be %s characters min" % MIN_PASSWORD_LENGTH)
        # Search users with same email
        if self.store.read_user_by_email(email):
            logger.debug("Email '%s' already exists!" % email)
            raise ControledErrorException("Email '%s' already exists! Forgot password? "
                                          "Go to login and click on forgot password" % email)

        try:
            brl_user = BRLUser(brl_user)
            bii_user = User(brl_user)
            bii_user.password = plain_password
        except InvalidNameException as e:
            raise ControledErrorException(e)

        # Search invited_by user (by mail or login)
        friend = None
        if invited_by:
            if "@" in invited_by:  # email address
                friend = self.store.read_user_by_email(invited_by)
                friend = friend.ID if friend else None
            else:  # Login
                friend_object = self.store.exists_user_id_ignoring_case(invited_by)
                if friend_object and friend_object.active:
                    friend = invited_by
            if not friend:
                raise ControledErrorException("User %s doesn't exist" % invited_by)
        bii_user.invited_by = friend

        # Check the existing of user name (User.ID), with case-insensitive
        if self.store.exists_user_id_ignoring_case(brl_user):
            logger.debug("User name '%s' already exists!" % brl_user)
            raise ControledErrorException("Username '%s' already exists! "
                                          "Choose other username" % brl_user)

        try:
            bii_user.email = email
            bii_user.allow_mailing = allow_mailing

            manager = JWTConfirmEmailManagerFactory.new()
            token = manager.get_token_for(brl_user)

            bii_user.confirmation_token = token
            bii_user.joined_date = datetime.datetime.now()
            bii_user.active = False

            oauth_service = get_oauth_service(self.store)
            oauth_user_info = oauth_service.get_user_info(provider, access_token)
            self.store.create_user(bii_user)

            if oauth_user_info:
                # If user has changed the oauth email, not confirm the account
                if oauth_user_info[1] == bii_user.email:
                    bii_user.active = True
                try:
                    register_signup(self.store, brl_user)
                except Exception as exc:
                    logger.error("Can't register sign-up in background! %s" % str(exc))

                bii_user.fill_user_oauth_token(provider, access_token)
                self.store.update_user(bii_user)

            return bii_user

        except Exception as e:
            logger.error("Error creating user at mongo: %s" % str(e))
            logger.error(traceback.format_exc())
            raise e

    def confirm_account(self, confirmation_token):
        '''
        Confirms user in database
        '''
        try:
            # Decode token
            jwt_manager = JWTConfirmEmailManagerFactory.new()
            brl_user = jwt_manager.get_confirmed_user(confirmation_token)
            user = self.store.read_user(brl_user)
        except NotInStoreException:
            raise NotFoundException("User '%s' doesn't exist" % brl_user)
        if user.confirmation_token == confirmation_token:
            if not user.active:  # Do not re-send things if already activated
                try:
                    register_signup(self.store, brl_user)
                except Exception as exc:
                    logger.error("Can't register sign-up in background! %s" % str(exc))

            user.active = True
            user.confirmation_date = datetime.datetime.now()
            self.store.update_user(user)
            jwt_auth_manager = JWTCredentialsManagerFactory.new(self.store)
            token = jwt_auth_manager.get_token_for(brl_user)

            return token, brl_user, user.ga_client_id

        else:
            raise NotFoundException("Invalid user or token")

    def confirm_password_reset(self, confirmation_token):
        '''
        Confirms password change. User and password are inside the token
        '''
        try:
            # Decode token
            jwt_manager = JWTPasswordResetManagerFactory.new()
            brl_user, plain_password = jwt_manager.get_user_and_password(confirmation_token)
            user = self.store.read_user(brl_user)
        except Exception:
            raise NotFoundException("No user found with name %s" % brl_user)
        # Update password
        user.password = plain_password
        user.active = True  # If not active, activate now, email is validated
        self.store.update_user(user)

        # Generate an auth token to autologin user
        jwt_auth_manager = JWTCredentialsManagerFactory.new(self.store)
        token = jwt_auth_manager.get_token_for(brl_user)
        return token, brl_user

    def update(self, brl_user, new_fields):
        try:
            self.security.check_update_user(brl_user)
            user = self.store.read_user(brl_user)
            user.firstname = new_fields["firstname"]
            user.lastname = new_fields["lastname"]
            user.country = new_fields["country"]
            user.description = new_fields["description"]
            user.street_1 = new_fields["street_1"]
            user.street_2 = new_fields["street_2"]
            user.city = new_fields["city"]
            user.postal_code = new_fields["postal_code"]
            user.region = new_fields["region"]
            user.tax_id = new_fields["tax_id"]
            user.vat = new_fields["vat"]
            # Tsgs is for internal use yet
            # user.tags = set(new_fields["tags"])
            user.visible_email = new_fields["visible_email"]
            user.allow_mailing = new_fields["allow_mailing"]

            self.store.update_user(user)
        except NotInStoreException:
            raise NotFoundException("No user found with name %s" % brl_user)

    def change_password(self, brl_user, old_password, new_plain_password):
        ''' Changes the password for the specified user'''
        logger.debug("Change password for user %s" % brl_user)
        self.security.check_change_password(brl_user)
        user = self.store.read_user(brl_user)
        if user.valid_password(old_password):
            logger.debug("old password ok")
            try:
                user.password = new_plain_password
            except InvalidNameException as e:
                raise ControledErrorException(e)
            self.store.update_user(user)
            logger.debug("Updated user!")
        else:
            raise ControledErrorException("Invalid password!")

    def authenticate(self, brl_user, password):
        """ Create a "profile" object (object to encrypt) and expiration time.
        Then return the JWT token Expiration time as a UTC UNIX timestamp
        (an int) or as a datetime"""
        try:
            brl_user = BRLUser(brl_user)
        except InvalidNameException:
            raise AuthenticationException("Wrong user or password")
        self._check_password(brl_user, password)
        manager = JWTCredentialsManagerFactory.new(self.store)
        token = manager.get_token_for(brl_user)
        return brl_user, token

    def _check_password(self, nickname, password):
        ''' Check user brl_user/password '''
        try:
            user = self.store.read_user(nickname)
        except Exception:
            raise AuthenticationException("Wrong user or password")
        if user.active:
            if not user.valid_password(password):
                raise AuthenticationException("Wrong user or password")
        else:
            raise NotActivatedUser("User email is not confirmed! "
                                   "We have sent an email to your account")


def user_to_json(user):
    ret = {"login": user.ID, "email": user.email, "firstname": user.firstname,
           "lastname": user.lastname, "country": user.country, "description": user.description,
           "visible_email": user.visible_email, "gravatar_hash": user.gravatar_email_hash,
           "allow_mailing": user.allow_mailing, "read_api_counter": user.read_api_counter,
           "publish_counter": user.publish_counter, "reuse_counter": user.reuse_counter,
           "street_1": user.street_1, "street_2": user.street_2, "city": user.city,
           "postal_code": user.postal_code, "region": user.region, "tax_id": user.tax_id, "vat": user.vat
           }

    ret["blocks"] = []
    for brl_block, block_meta in user.blocks.iteritems():
        ret["blocks"].append(_user_block_to_json(brl_block, block_meta))
    return ret


def _user_block_to_json(brl_block, block_meta, gravatar_hash=None):
    return {"creator": brl_block.creator,
            "owner": brl_block.owner,
            "branch": brl_block.branch,
            "block_name": brl_block.block_name.name,
            "tags": list(block_meta[0]),
            "description": block_meta[1],  # Meta [2] is block size
            "private": block_meta[-1],  # Appended in line 78, last one is privacy
            "gravatar_hash": gravatar_hash,
            }
