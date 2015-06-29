import unittest
from biicode.server.model.social_account import SocialAccount, SocialAccountToken
from biicode.server.model.epoch.utc_datetime import UtcDatetime
import datetime


class SocialAccountTest(unittest.TestCase):
    def setUp(self):
        self.utc_datetime = UtcDatetime.deserialize(datetime.datetime.now())

    def test_social_token_serialization(self):
        social_token = SocialAccountToken("xxzc", "zxcc", self.utc_datetime)
        serialized_social_token = social_token.serialize()
        self.assertEquals(SocialAccountToken.deserialize(serialized_social_token), social_token)

    def test_social_token_no_secret_serialization(self):
        social_token = SocialAccountToken("xxzc", "", self.utc_datetime)
        serialized_social_token = social_token.serialize()
        self.assertEquals(SocialAccountToken.deserialize(serialized_social_token), social_token)

    def test_social_account_serialization(self):
        tokens = [SocialAccountToken("xxzc", "zxcc", self.utc_datetime),
                  SocialAccountToken("xxzc", "zxcc", self.utc_datetime)]

        social_account = SocialAccount("zcas",
                                       self.utc_datetime,
                                       self.utc_datetime,
                                       tokens,
                                       "zcc")

        serialized_social_account = social_account.serialize()
        self.assertEquals(SocialAccount.deserialize(serialized_social_account), social_account)

    def test_social_account_without_token_serialization(self):
        tokens = []

        social_account = SocialAccount("zcas",
                                       self.utc_datetime,
                                       self.utc_datetime,
                                       tokens,
                                       "zcc")

        serialized_social_account = social_account.serialize()
        self.assertEquals(SocialAccount.deserialize(serialized_social_account), social_account)
