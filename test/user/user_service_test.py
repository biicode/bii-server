from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.user.jwt_accounts_manager import JWTConfirmEmailManagerFactory
from biicode.server.user.user_service import UserService
from biicode.server.api.jwt_credentials_manager import JWTCredentialsManagerFactory
from time import sleep
from biicode.test.remote.testing_mongo_store import TestingMongoStore
from jwt import DecodeError
from mock import patch, Mock
from biicode.server.exception import ControledErrorException


class UserServiceTest(TestWithMongo):

    def setUp(self, *args, **kwargs):
        self.store = TestingMongoStore(self.conn, self.database_name)
        _, self.brl_user = self.store.generate_non_persistent_user()
        self.user_service = UserService(self.store, self.brl_user)
        self.email = "%s@fake.com" % self.brl_user
        self.plain_password = "kaKePass"
        allow_mailing = False
        self.bii_user = self.user_service.register(self.brl_user, self.email,
                                                   self.plain_password, allow_mailing)
        self.manager = JWTConfirmEmailManagerFactory.new()
        _, self.confirmed_user, _ = self.user_service.confirm_account(self.bii_user.confirmation_token)

    def test_used_register(self):
        '''Resgister and confirm user'''
        self.assertEqual(self.bii_user.ID, self.confirmed_user)

    def test_invite_register(self):
        # Input login ok
        self.user_service.register("newuser", "newuser@fake.com", self.plain_password,
                                   True, invited_by=self.brl_user)
        saved_user = self.store.read_user("newuser")
        self.assertEquals(saved_user.invited_by, self.brl_user)

        # Input login bad (not exist)
        self.assertRaises(ControledErrorException, self.user_service.register,
                          "newuser2", "newuser2@fake.com", self.plain_password,
                          True, invited_by="noexistuser")

        # Input by email ok
        self.user_service.register("newuser2", "newuser2@fake.com", self.plain_password,
                                   True, invited_by=self.email)
        saved_user = self.store.read_user("newuser2")
        self.assertEquals(saved_user.invited_by, self.brl_user)

        # Input by email error
        self.assertRaises(ControledErrorException, self.user_service.register,
                          "newuser3", "newuser3@fake.com", self.plain_password,
                          True, invited_by="NOT@email.com")

    def test_invalid_token(self):
        '''Obtain a valid token and then change password. Token must be invalid'''
        brl_user, token_1 = self.user_service.authenticate(self.brl_user, self.plain_password)
        # Check the token is valid
        manager = JWTCredentialsManagerFactory.new(self.store)
        brl_user_test = manager.get_user(token_1)
        self.assertEqual(brl_user, brl_user_test)
        sleep(0.1)  # Sleep a moment and change the password

        # Now change password and re-check old token
        self.user_service.change_password(self.brl_user, self.plain_password, "Newp@sW0rd")

        # Check the token is invalid (can't authenticate)
        self.assertRaises(DecodeError, manager.get_user, token_1)

    @patch('biicode.server.user.user_service.get_oauth_service')
    def test_oauth_register(self, get_oauth_service):

        # Check that if provider and access_token is passed to register, user
        # is activated automatically and access_token is stored in user
        email = "new_user1@biicode.com"
        _, brl_user = self.store.generate_non_persistent_user()

        oauth_service = Mock()
        oauth_service.get_user_info = Mock(return_value=(brl_user, email))
        get_oauth_service.return_value = oauth_service

        self.bii_user = self.user_service.register(brl_user, email,
                                                   self.plain_password, True,
                                                   "google", "THE_ACCESS_TOKEN")

        saved_user = self.store.read_user(brl_user)
        self.assertEqual(saved_user.oauth_google_token, "THE_ACCESS_TOKEN")
        self.assertIsNone(saved_user.oauth_github_token)
        self.assertEqual(saved_user.active, True)

        # Now check the github token
        email = "new_user2@biicode.com"
        _, brl_user = self.store.generate_non_persistent_user()

        oauth_service = Mock()
        oauth_service.get_user_info = Mock(return_value=(brl_user, email))
        get_oauth_service.return_value = oauth_service

        self.bii_user = self.user_service.register(brl_user, email,
                                                   self.plain_password, True,
                                                   "github", "THE_GITHUB_ACCESS_TOKEN")

        saved_user = self.store.read_user(brl_user)
        self.assertEqual(saved_user.oauth_github_token, "THE_GITHUB_ACCESS_TOKEN")
        self.assertIsNone(saved_user.oauth_google_token)
        self.assertEqual(saved_user.active, True)

        # Now check that if email has been changed in registration process
        # user is not auto activated, but token is stored
        email = "new_user3@biicode.com"
        _, brl_user = self.store.generate_non_persistent_user()

        oauth_service = Mock()
        oauth_service.get_user_info = Mock(return_value=(brl_user, "othermail@biicode.com"))
        get_oauth_service.return_value = oauth_service

        self.bii_user = self.user_service.register(brl_user, email,
                                                   self.plain_password, True,
                                                   "github", "THE_GITHUB_ACCESS_TOKEN")

        saved_user = self.store.read_user(brl_user)
        self.assertEqual(saved_user.oauth_github_token, "THE_GITHUB_ACCESS_TOKEN")
        self.assertIsNone(saved_user.oauth_google_token)
        self.assertEqual(saved_user.active, False)

        # Finally if get user info returns none (invalid token) nothing registration process keeps
        # normal
        email = "new_user4@biicode.com"
        _, brl_user = self.store.generate_non_persistent_user()

        oauth_service = Mock()
        oauth_service.get_user_info = Mock(return_value=None)
        get_oauth_service.return_value = oauth_service

        self.bii_user = self.user_service.register(brl_user, email,
                                                   self.plain_password, True,
                                                   "github", "THE_GITHUB_ACCESS_TOKEN")

        saved_user = self.store.read_user(brl_user)
        self.assertIsNone(saved_user.oauth_github_token)
        self.assertIsNone(saved_user.oauth_google_token)
        self.assertEqual(saved_user.active, False)
