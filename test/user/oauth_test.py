from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.test.remote.testing_mongo_store import TestingMongoStore
from biicode.server.user.oauth import OAuthService, generate_state_string
from biicode.server.model.user import User


class MockOAuthManager(object):

    def __init__(self, provider, brl_user):
        self.provider = provider
        self.brl_user = brl_user

    def get_url_for_provider_login(self, state_string):
        return "url for %s login" % self.provider

    def get_access_token(self, code):
        return "ACCESS_TOKEN_%s_%s" % (self.provider, self.brl_user)

    def get_user_info(self, access_token):
        if access_token == "ACCESS_TOKEN_%s_%s" % (self.provider, self.brl_user):
            return self.brl_user, "%s@biicode.com" % self.brl_user
        else:
            return None


class OAuthServiceTest(TestWithMongo):

    def setUp(self, *args, **kwargs):
        self.store = TestingMongoStore(self.conn, self.database_name)

    def test_get_login_url(self):
        managers = {"google": MockOAuthManager("google", "user1"),
                    "github": MockOAuthManager("github", "user1")}
        oauth_service = OAuthService(self.store, managers)

        login_url = oauth_service.get_url_for_provider_login("google")
        self.assertEqual(login_url, "url for google login")

        login_url = oauth_service.get_url_for_provider_login("github")
        self.assertEqual(login_url, "url for github login")

    def test_login_and_register(self):

        # User exists with same token, url must be login url
        uid, brl_user = self.store.generate_non_persistent_user()
        managers = {"google": MockOAuthManager("google", brl_user),
                    "github": MockOAuthManager("github", brl_user)}
        oauth_service = OAuthService(self.store, managers)
        user = User(brl_user)
        user.oauth_google_token = "ACCESS_TOKEN_google_%s" % brl_user
        self.store.create_user(user, uid)
        state_string = generate_state_string("google")
        url = oauth_service.handle_register_or_login(state_string, "somecode")
        self.assertIn("/accounts/login?", url)

        # User exists but not token, just email, so user is saved
        # with access token and go to login
        uid, brl_user = self.store.generate_non_persistent_user()
        managers = {"google": MockOAuthManager("google", brl_user),
                    "github": MockOAuthManager("github", brl_user)}
        oauth_service = OAuthService(self.store, managers)
        user = User(brl_user)
        user.email = "%s@biicode.com" % brl_user
        self.store.create_user(user, uid)
        state_string = generate_state_string("github")
        url = oauth_service.handle_register_or_login(state_string, "somecode")
        user = self.store.read_user(brl_user)
        self.assertEquals(user.oauth_github_token, "ACCESS_TOKEN_github_%s" % brl_user)
        self.assertIn("/accounts/login?", url)

        # User NO NOT exist (token nor email are found)
        # with access token and go to register page
        managers = {"google": MockOAuthManager("google", "fakeuser"),
                    "github": MockOAuthManager("github", "fakeuser")}
        oauth_service = OAuthService(self.store, managers)
        state_string = generate_state_string("github")
        url = oauth_service.handle_register_or_login(state_string, "somecode")
        self.assertIn("/accounts/signup?access_token=ACCESS_TOKEN_github", url)
        self.assertIn("provider=github", url)
