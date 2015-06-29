import unittest
from biicode.server.model.user import User
from biicode.server.model.epoch.utc_datetime import UtcDatetime
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.exception import ForbiddenException, BiiException
from biicode.server.exception import DuplicateBlockException
from biicode.common.model.id import ID
from biicode.server.model.social_account import SocialAccount, SocialAccountToken
import datetime


class UserTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.user = User("laso")
        self.user.password = "password"
        self.user.numeric_id = ID((22, ))
        self.user.firstname = "Jose"
        self.user.lastname = "Gomez"
        self.user.country = "ES"
        self.user.description = "Developer"
        self.user.email = "pepe@pepedomain.com"
        self.user.visible_email = True
        self.user.allow_mailing = True
        self.user.active = True
        self.user.staff = False
        self.user.joined_date = UtcDatetime.get_current_utc_datetime()
        self.user.last_api_call = UtcDatetime.get_current_utc_datetime()
        self.user.add_block(BRLBlock("laso/laso/block/master"), ["arduino"])
        # Profile fields
        self.user.street_1 = "Melancolia Street"
        self.user.street_2 = "123"
        self.user.city = "Madrid"
        self.user.postal_code = "28027"
        self.user.region = "Madrid"
        self.user.vat = "B81884306"
        self.user.tax_id = "ESB81884306"
        self.utc_datetime = UtcDatetime.deserialize(datetime.datetime.now())

    def test_serialization(self):

        self.user.add_block(BRLBlock("laso/laso/block2/master"),
                            tags=["ONE", "TWO"],
                            description="The good block")
        self.user.add_block(BRLBlock("laso/laso/block3/master"))

        self.user.administrators.grant("pepito")
        self.user.administrators.grant("josete")

        tokens = [SocialAccountToken("xxzc", "zxcc", self.utc_datetime),
                  SocialAccountToken("xxzc", "zxcc", self.utc_datetime)]

        social_account = SocialAccount("zcas",
                                       self.utc_datetime,
                                       self.utc_datetime,
                                       tokens,
                                       "zcc")

        self.user.social_accounts = {"google": social_account}
        self.user.publish_counter = 10
        self.user.reuse_counter = 7
        self.user.read_api_counter = 99

        seri = self.user.serialize()
        user2 = User.deserialize(seri)
        self.assertTrue(self._user_equal(self.user, user2))
        self.assertEqual(user2.read_api_counter, 99)
        self.assertEqual(user2.reuse_counter, 7)
        self.assertEqual(user2.publish_counter, 10)
        self.assertEqual(set(user2.administrators), {"pepito", "josete"})

        self.assertEqual(self.user.region, "Madrid")

    def test_add_repeated_block(self):
        brlb = BRLBlock("laso/laso/block/master")
        self.assertRaises(DuplicateBlockException, self.user.add_block, brlb)

    def test_create_duplicate_block_different_case(self):
        ''' Attempt to create two blocks with diferent casing eg: MyBlock and myblock '''
        name1 = BRLBlock('%s/%s/testblock/trunk' % (self.user.ID, self.user.ID))
        name2 = BRLBlock('%s/%s/TestBlock/trunk' % (self.user.ID, self.user.ID))
        self.user.add_block(name1)
        with self.assertRaisesRegexp(BiiException, 'There is already a block named'):
            self.user.add_block(name2)

    def test_add_tag_to_block(self):
        brlb = BRLBlock("laso/laso/block2/master")
        self.user.add_block(brlb)
        self.user.add_block_tag(brlb, "arduino")
        self.assertEquals(self.user.get_block_tags(brlb), set(["arduino"]))

    def test_add_block_with_tag(self):
        brlb = BRLBlock("laso/laso/block2/master")
        self.user.add_block(brlb, tags=["arduino"])
        self.assertEquals(self.user.get_block_tags(brlb), set(["arduino"]))

    def test_change_block_description(self):
        brlb = BRLBlock("laso/laso/block/master")
        self.user.set_block_description(brlb, "other")
        self.assertEquals(self.user.get_block_description(brlb), "other")

    def test_forbidden(self):
        brlb = BRLBlock(name="novita/laso/theblock/master")
        self.assertRaises(ForbiddenException, self.user.add_block, brlb)

    def _user_equal(self, user, other):
        '''Equals method'''
        if user is other:
            return True
        return isinstance(other, user.__class__) \
            and user.ID == other.ID \
            and user.numeric_id == other.numeric_id \
            and user._encrypted_password == other._encrypted_password \
            and user.firstname == other.firstname \
            and user.lastname == other.lastname \
            and user.country == other.country \
            and user.description == other.description \
            and user.email == other.email \
            and user.visible_email == other.visible_email \
            and user.allow_mailing == other.allow_mailing \
            and user.active == other.active \
            and user.staff == other.staff \
            and user.joined_date == other.joined_date \
            and user.confirmation_date == other.confirmation_date \
            and user.confirmation_token == other.confirmation_token \
            and user.block_counter == other.block_counter \
            and user.blocks == other.blocks \
            and user.administrators == other.administrators \
            and user.read_api_counter == other.read_api_counter \
            and user.publish_counter == other.publish_counter \
            and user.street_1 == other.street_1 \
            and user.street_2 == other.street_2 \
            and user.city == other.city \
            and user.postal_code == other.postal_code \
            and user.region == other.region \
            and user.tax_id == other.tax_id\
            and user.vat == other.vat
