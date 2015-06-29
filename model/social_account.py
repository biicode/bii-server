from biicode.common.utils.serializer import Serializer, ListDeserializer
from biicode.server.model.epoch.utc_datetime import UtcDatetime


class SocialAccountToken(object):
    SERIAL_TOKEN = 't'
    SERIAL_TOKEN_SECRET = 's'
    SERIAL_EXPIRE_DATE = 'e'

    def __init__(self, token, token_secret, expire_date):
        self.token = token
        self.token_secret = token_secret
        self.expire_date = expire_date

    def serialize(self):
        return Serializer().build(
            (self.SERIAL_TOKEN, self.token),
            (self.SERIAL_TOKEN_SECRET, self.token_secret),
            (self.SERIAL_EXPIRE_DATE, self.expire_date))

    @classmethod
    def deserialize(cls, doc):
        token = doc.get(cls.SERIAL_TOKEN)
        token_secret = doc.get(cls.SERIAL_TOKEN_SECRET)
        expire_date = UtcDatetime.deserialize(doc.get(cls.SERIAL_EXPIRE_DATE))
        return SocialAccountToken(token, token_secret, expire_date)

    def __eq__(self, other):
        if self is other:
            return True
        return self.token == other.token \
            and self.token_secret == other.token_secret \
            and self.expire_date == other.expire_date


class SocialAccount(object):
    #SERIAL_PROVIDER = "p"
    SERIAL_UID = "u"
    SERIAL_LAST_LOGIN = "l"
    SERIAL_DATE_JOINED = "d"
    SERIAL_TOKENS = "t"
    SERIAL_EXTRA_DATA = "e"

    def __init__(self, uid, last_login, date_joined, tokens, extra_data=None):
        #self.provider = provider
        self.uid = uid
        self.last_login = last_login
        self.date_joined = date_joined
        self.tokens = tokens
        self.extra_data = extra_data

    def serialize(self):
        return Serializer().build(
                #(self.SERIAL_PROVIDER, self.provider),
                (self.SERIAL_UID, self.uid),
                (self.SERIAL_LAST_LOGIN, self.last_login),
                (self.SERIAL_DATE_JOINED, self.date_joined),
                (self.SERIAL_TOKENS, self.tokens),
                (self.SERIAL_EXTRA_DATA, self.extra_data)
                )

    @classmethod
    def deserialize(cls, doc):
        #provider = doc.get(SocialAccount.SERIAL_PROVIDER)
        uid = doc.get(cls.SERIAL_UID)
        last_login = UtcDatetime.deserialize(doc.get(cls.SERIAL_LAST_LOGIN))
        date_joined = UtcDatetime.deserialize(doc.get(cls.SERIAL_DATE_JOINED))
        tokens = ListDeserializer(SocialAccountToken).deserialize(doc.get(cls.SERIAL_TOKENS))
        extra_data = doc.get(cls.SERIAL_EXTRA_DATA)
        return SocialAccount(uid, last_login, date_joined, tokens, extra_data)

    def __eq__(self, other):
        if self is other:
            return True
        return self.uid == other.uid \
            and self.last_login == other.last_login \
            and self.date_joined == other.date_joined \
            and self.tokens == other.tokens \
            and self.extra_data == other.extra_data
