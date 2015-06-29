from biicode.server.conf import BII_GITHUB_OAUTH_CLIENT_ID,\
    BII_OAUTH_STATE_STRING_GENERATOR_KEY, BII_GITHUB_OAUTH_CLIENT_SECRET,\
    BII_WEB_DOMAIN_URL, BII_GOOGLE_OAUTH_CLIENT_ID,\
    BII_GOOGLE_OAUTH_CLIENT_SECRET, BII_OAUTH_CONTROLLER_URL
from datetime import timedelta
from biicode.server.api.jwt_manager import JWTManager
from biicode.common.exception import BiiException
import requests
from biicode.server.api.jwt_credentials_manager import JWTCredentialsManagerFactory
import urllib


manager = JWTManager(BII_OAUTH_STATE_STRING_GENERATOR_KEY, timedelta(minutes=60))


def generate_state_string(provider):
    # Generate an encrypted string so we can decrypt later
    # and know if we started the process or if its initiated by us
    # returns an unguessable random string.
    # It is used to protect against cross-site request forgery attacks.
    return manager.get_token_for({"provider": provider})


def validate_state_string(state_string):
    try:
        return manager.get_profile(state_string)["provider"]
    except Exception:
        return False


def get_oauth_service(store):
    managers = {"github": GitHubOAuthManager(), "google": GoogleOAuthManager()}
    return OAuthService(store, managers)


class OAuthService(object):

    def __init__(self, store, managers):
        self.store = store
        self.managers = managers

    def get_user_info(self, provider, token):
        '''returns a tuple with login and email from oauth provider'''
        if not provider or not token:
            return False

        manager = self.manager_factory(provider)
        try:
            user_info = manager.get_user_info(token)
            return user_info
        except:
            return None

    def get_url_for_provider_login(self, provider):
        '''URL of the page where the user accepts application'''
        manager = self.manager_factory(provider)
        if not manager:
            raise BiiException()
        state_string = generate_state_string(provider)

        return manager.get_url_for_provider_login(state_string)

    def manager_factory(self, provider):
        return self.managers.get(provider, None)

    def handle_register_or_login(self, state_string, code):
        '''Call the oauth service and obtain the access_token.
           Search for the user in biicode database and login or
           register'''
        provider = validate_state_string(state_string)
        manager = self.manager_factory(provider)
        access_token = manager.get_access_token(code)

        user_info = manager.get_user_info(access_token)
        if not user_info:
            return ""

        login, email = user_info

        # User exist and have token
        user = self.store.read_user_by_oauth_token(provider, access_token)

        if user:
            # Login
            return self._get_login_page(user)
        else:
            # Try to find by email
            user = self.store.read_user_by_email(email)
            if user:
                # Save token
                user.fill_user_oauth_token(provider, access_token)
                self.store.update_user(user)
                # return Login URL
                return self._get_login_page(user)
            else:
                # Go to register page with filled data
                return self._get_register_page(login, email, access_token, provider)

    def _get_login_page(self, user):
        manager = JWTCredentialsManagerFactory.new(self.store)
        token = manager.get_token_for(user.ID)

        joined_date = user.joined_date.to_iso8601 if user and user.joined_date else ""
        get_vars = {"oauthlogin": 1,
                    "login": user.ID, "token": token,
                    "client_id": user.ga_client_id,
                    "email": user.email, "created_at": joined_date}
        return "%s/accounts/login?%s" % (BII_WEB_DOMAIN_URL, urllib.urlencode(get_vars))

    def _get_register_page(self, login, email, access_token, provider):
        get_vars = {"login": login, "email": email,
                    "access_token": access_token, "provider": provider}
        return "%s/accounts/signup?%s" % (BII_WEB_DOMAIN_URL, urllib.urlencode(get_vars))


class GitHubOAuthManager(object):

    scope = "user:email"

    def get_url_for_provider_login(self, state_string):
        client_id = BII_GITHUB_OAUTH_CLIENT_ID
        params = {"client_id": client_id, "state": state_string, "scope": self.scope}
        return "https://github.com/login/oauth/authorize?" + urllib.urlencode(params)

    def get_access_token(self, code):
        payload = {'client_id': BII_GITHUB_OAUTH_CLIENT_ID,
                   'client_secret': BII_GITHUB_OAUTH_CLIENT_SECRET,
                   'code': code}
        headers = {'Accept':  'application/json'}

        res = requests.post('https://github.com/login/oauth/access_token', params=payload,
                            headers=headers)
        json = res.json()

        if "error" in json:
            raise BiiException(json["error"])
        if json.get("scope", None) != self.scope:
            return BiiException(json["Biicode needs your email and login"])
        return json["access_token"]

    def get_user_info(self, access_token):
        res = requests.get('https://api.github.com/user',
                           params={"access_token": access_token})
        json = res.json()
        email = self._get_user_email(access_token)
        if not email:
            return None

        return json["login"], email

    def _get_user_email(self, access_token):
        res = requests.get('https://api.github.com/user/emails',
                           params={"access_token": access_token})
        emails = res.json()
        if not emails:
            return None

        for email in emails:
            if email["primary"]:
                return email["email"]

        return emails[0]["email"]  # No primary email


class GoogleOAuthManager(object):

    scope = "https://www.googleapis.com/auth/userinfo.email"

    def get_url_for_provider_login(self, state_string):
        client_id = BII_GOOGLE_OAUTH_CLIENT_ID
        params = {"client_id": client_id, "state": state_string,
                  "scope": self.scope, "response_type": "code",
                  "redirect_uri": BII_OAUTH_CONTROLLER_URL}
        return "https://accounts.google.com/o/oauth2/auth?" + urllib.urlencode(params)

    def get_access_token(self, code):
        payload = {'client_id': BII_GOOGLE_OAUTH_CLIENT_ID,
                   'client_secret': BII_GOOGLE_OAUTH_CLIENT_SECRET,
                   'code': code,
                   'grant_type': 'authorization_code',
                   'redirect_uri': BII_OAUTH_CONTROLLER_URL}

        headers = {'Accept':  'application/json'}

        res = requests.post('https://www.googleapis.com/oauth2/v3/token', params=payload,
                            headers=headers)

        json = res.json()

        if "error" in json:
            raise BiiException(json["error"])
        return json["access_token"]

    def get_user_info(self, access_token):
        params = {"alt": "json", "access_token": access_token}
        encoded_params = urllib.urlencode(params)
        url = 'https://www.googleapis.com/oauth2/v1/userinfo?%s' % encoded_params
        res = requests.get(url)
        json = res.json()
        login = json["email"].split("@")[0].replace(".", "_")
        if not json["email"]:
            return None

        return login, json["email"]
