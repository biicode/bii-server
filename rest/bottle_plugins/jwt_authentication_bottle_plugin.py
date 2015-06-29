from bottle import HTTPResponse
from biicode.server.rest.bottle_plugins.authorization_header import AuthorizationHeaderBottlePlugin


class JWTAuthenticationBottlePlugin(AuthorizationHeaderBottlePlugin):
    ''' The HttpBasicAuthenticationBottlePlugin plugin requires Http Basic Authentication'''

    name = 'jwtauthenticationbottleplugin'
    api = 2

    def __init__(self, manager, keyword='auth_user'):
        '''Manager should be a JWTCredentialsManager'''
        self.manager = manager
        self.keyword = keyword
        super(JWTAuthenticationBottlePlugin, self).__init__(keyword)

    def get_authorization_type(self):
        return "Bearer"

    def parse_authorization_value(self, header_value):
        """Parse header_value and return kwargs to apply bottle
        method parameters"""
        try:
            if not header_value:
                username = None
            else:
                # Check if its valid obtaining the password_timestamp
                username = self.manager.get_user(token=header_value)
        except Exception:
            # Check if
            resp = HTTPResponse("Wrong JWT token!", "401 Unauthorized")
            resp.set_header('Content-Type', 'text/plain')
            raise resp
        return {self.keyword: username}

    def get_invalid_header_response(self):
        """A response from a malformed header. Includes WWW-Authenticate for
        ask browser to request user and password"""
        return HTTPResponse("'Http Authentication not implemented'",
                            "401 Unauthorized")
