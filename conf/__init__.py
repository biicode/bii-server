import os
from datetime import timedelta
from biicode.common.model.server_info import ClientVersion
from biicode.common.conf.configure_environment import get_env
from biicode.common.conf import MEGABYTE

BII_MONGO_URI = get_env('BII_MONGO_URI', "mongodb://localhost:27017/biidb")
BIISERVER_RUN_PORT = get_env('PORT', 9000)  # Heroku runs on their PORT environment
BIIWEBAPI_RUN_PORT = get_env('PORT', 9200)  # Heroku runs on their PORT environment
BII_MEMCACHE_SERVERS = get_env('MEMCACHIER_SERVERS', None)  # Heroku need
BII_MEMCACHE_USERNAME = get_env('MEMCACHIER_USERNAME', None)  # Heroku need
BII_MEMCACHE_PASSWORD = get_env('MEMCACHIER_PASSWORD', None)  # Heroku need
BII_MEMCACHE_BLOCK_PERMISSIONS_EXPIRE_MINUTES = timedelta(minutes=get_env('BII_MEMCACHE_BLOCK_PERMISSIONS_EXPIRE_MINUTES', 480))  # 8h
BII_MEMCACHE_HIVE_PERMISSIONS_EXPIRE_MINUTES = timedelta(minutes=get_env('BII_MEMCACHE_HIVE_PERMISSIONS_EXPIRE_MINUTES', 60))  # 1h
BII_MEMCACHE_SUBS_PERMISSIONS_EXPIRE_MINUTES = timedelta(minutes=get_env('BII_MEMCACHE_SUBS_PERMISSIONS_EXPIRE_MINUTES', 480))  # 8h

BII_DOS_ATTACK_MAX_REQUEST = get_env('BII_DOS_ATTACK_MAX_REQUEST', 10000)  # Max request in BII_DOS_ATTACK_DELTA_TIME
BII_DOS_ATTACK_DELTA_TIME = timedelta(seconds=get_env('BII_DOS_ATTACK_DELTA_TIME', 10))  # Max request in 1 second
BII_DOS_ATTACK_BAN_TIME = timedelta(seconds=get_env('BII_DOS_ATTACK_BAN_TIME', 3600))  # Banned for an hour
BII_DOS_ATTACK_BODY_RESPONSE = get_env('BII_DOS_ATTACK_BODY_RESPONSE', '')
BII_DOS_ATTACK_STATUS_RESPONSE = get_env('BII_DOS_ATTACK_STATUS_RESPONSE', '401 Unauthorized')
# TODO: BII_DOS_ATTACK_HEADERS_RESPONSE = os.getenv('BII_DOS_ATTACK_HEADERS_RESPONSE', {"WWW-Authenticate": 'Basic realm="Login Required"'})

# Max request in BII_ERROR_ATTACK_DELTA_TIME
BII_ERROR_ATTACK_MAX_ATTEMPTS = get_env('BII_ERROR_ATTACK_MAX_ATTEMPTS', 30)
# Max request in 1 minute
BII_ERROR_ATTACK_DELTA_TIME = timedelta(seconds=get_env('BII_ERROR_ATTACK_DELTA_TIME', 60))
# Banned for an hour
BII_ERROR_ATTACK_BAN_TIME = timedelta(seconds=get_env('BII_ERROR_ATTACK_BAN_TIME', 3600))
BII_ERROR_ATTACK_BODY_RESPONSE = get_env('BII_ERROR_ATTACK_BODY_RESPONSE', '')
BII_ERROR_ATTACK_STATUS_RESPONSE = get_env('BII_ERROR_ATTACK_STATUS_RESPONSE',
                                             '401 Unauthorized')

BII_SSL_ENABLED = get_env('BII_SSL_ENABLED', False)

BII_SMTP_SERVER = get_env('BII_SMTP_SERVER', 'smtp.gmail.com')
BII_SMTP_PORT = get_env('BII_SMTP_PORT', 587)
BII_SMTP_USER = get_env('MANDRILL_USERNAME', 'fake@gmail.com')
BII_SMTP_PASSWORD = get_env('MANDRILL_APIKEY', 'fakepass')
BII_SMTP_USE_TLS = get_env('BII_SMTP_USE_TLS', True)
BII_DEFAULT_FROM_EMAIL = get_env('BII_DEFAULT_FROM_EMAIL', "fake@gmail.com")

BII_PRODUCTION_ENVIRONMENT = get_env('BII_PRODUCTION_ENVIRONMENT', False)

REDIS_URL = get_env('REDISTOGO_URL', 'redis://localhost:6379')
BII_DOWNLOAD_URL = get_env("BII_DOWNLOAD_URL", 'https://www.biicode.com/downloads')
BII_GREET_MSG = get_env("BII_GREET_MSG", '')
BII_LAST_COMPATIBLE_CLIENT = ClientVersion(get_env("BII_LAST_COMPATIBLE_CLIENT", '1.0'))

BII_MAX_MONGO_POOL_SIZE = get_env("BII_MAX_MONGO_POOL_SIZE", 100)

BII_JWT_SECRET_KEY = get_env('BII_JWT_SECRET_KEY', 'fakejwtsecretjkey')
BII_AUTH_TOKEN_EXPIRE_MINUTES = timedelta(minutes=get_env('BII_AUTH_TOKEN_EXPIRE_MINUTES', 30.0))

# Mailer settings
BII_MANDRILL_API_KEY = get_env('BII_MANDRILL_API_KEY', "fakemandrillapikey")
BII_MAIL_FROM = get_env('BII_MAIL_FROM', "info@biicode.com")
BII_NAME_FROM = get_env('BII_NAME_FROM', "Biicode")

# Secret for generate email confirmation tokens
BII_JWT_SECRET_MAIL_CONFIRMATION = get_env('BII_JWT_SECRET_MAIL_CONFIRMATION',
                                              "fakekeyfordevelop")
BII_JWT_SECRET_PASS_CHANGE = get_env('BII_JWT_SECRET_PASS_CHANGE', "fakekey2fordevelop")
# 1 day to change the password if requested token
BII_JWT_SECRET_PASS_CHANGE_EXPIRE_TIME = timedelta(
                                          days=get_env('BII_SECRET_PASS_CHANGE_EXPIRE_TIME', 1.0))
BII_MIXPANEL_TOKEN = get_env('BII_MIXPANEL_TOKEN', "invalidToken")
BII_API_MIXPANEL_EVENT_NAME = get_env('BII_API_MIXPANEL_EVENT_NAME', "bii_api_call")


# Have to be 32 bytes key
BII_AES_SECRET_KEY = get_env('BII_AES_SECRET_KEY', 'fakeaessecretkey')

BII_GA_API_KEY = get_env('BII_GA_API_KEY', '')

# in bytes
BII_MAX_MEMORY_PER_REQUEST = get_env('BII_MAX_MEMORY_PER_REQUEST', MEGABYTE * 12)

# Enable BiiUserTraceBottlePlugin
BII_ENABLED_BII_USER_TRACE = get_env('BII_ENABLED_BII_USER_TRACE', True)

# Background variables
import ast


BII_ANALYTIC_REDIS_URL = get_env("BII_ANALYTIC_REDIS_URL", "redis://localhost:6379")
BII_LOG_TO_REDIS = get_env('BII_LOG_TO_REDIS', True)

# Stripe
BII_STRIPE_API_KEY = get_env("BII_STRIPE_API_KEY", "sk_test_uD5YIDzUJszoRoSIh4EwURg6")


# Web domain (used in oauth and mailing)
BII_WEB_DOMAIN_URL = get_env('BII_WEB_DOMAIN_URL', "http://localhost:9100/#")

# Oauth
BII_GITHUB_OAUTH_CLIENT_ID = get_env("BII_GITHUB_OAUTH_CLIENT_ID", "")
BII_GITHUB_OAUTH_CLIENT_SECRET = get_env("BII_GITHUB_OAUTH_CLIENT_SECRET", "")

BII_GOOGLE_OAUTH_CLIENT_ID = get_env("BII_GOOGLE_OAUTH_CLIENT_ID", " ")
BII_GOOGLE_OAUTH_CLIENT_SECRET = get_env("BII_GOOGLE_OAUTH_CLIENT_SECRET", "")

BII_OAUTH_CONTROLLER_URL = get_env('BII_OAUTH_CONTROLLER_URL', "http://localhost:9200/v1/oauth")

BII_OAUTH_STATE_STRING_GENERATOR_KEY = get_env("BII_OAUTH_STATE_STRING_GENERATOR_KEY", "")

# MAX_USER BLOCKS SIZE

BII_MAX_USER_WORKSPACE_SIZE = get_env("BII_MAX_USER_WORKSPACE_SIZE", MEGABYTE*300)
