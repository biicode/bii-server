from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.utils.serializer import Serializer, DictDeserializer, SetDeserializer
from biicode.server.model.epoch.utc_datetime import UtcDatetime
from biicode.common.exception import InvalidNameException, ForbiddenException, BiiException
from biicode.server.exception import DuplicateBlockException
import hashlib
from biicode.server.model.permissions.permissions import Permissions
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.id import ID
from biicode.server.utils.passlib_pbkdf2_sha512_wrapper import encrypt, verify
from biicode.server.model.social_account import SocialAccount
import time
from biicode.server.utils.encryption import AESEncryption
from biicode.server.conf import BII_AES_SECRET_KEY, BII_MAX_USER_WORKSPACE_SIZE


class User(object):
    SERIAL_ID_KEY = '_id'
    SERIAL_ENCRYPTED_PASSWORD = "p"
    SERIAL_PASSWORD_TIMESTAMP = "pt"
    # Profile data
    SERIAL_FIRSTNAME = "f"
    SERIAL_LASTNAME = "l"
    SERIAL_COUNTRY = "c"
    SERIAL_DESCRIPTION = "d"
    SERIAL_EMAIL = "e"
    SERIAL_VISIBLE_EMAIL = "v"
    SERIAL_ALLOW_MAILING = "a"
    SERIAL_ACTIVE = "u"
    SERIAL_STAFF = "s"
    SERIAL_JOINED_DATE = "j"
    SERIAL_CONFIRMATION_DATE = "cd"
    SERIAL_CONFIRMATION_TOKEN = "ct"
    # Old user workspace fields
    SERIAL_MOD_COUNTER = 'wc'
    SERIAL_BLOCKS = 'wb'
    SERIAL_HIVES = 'wh'
    SERIAL_ADMINISTRATORS = 'wa'
    SERIAL_NUMERIC_ID = 'n'
    SERIAL_SOCIAL_ACCOUNTS = 'sa'

    # Achievements
    SERIAL_READ_API_COUNTER = 'ac1'
    SERIAL_PUBLISH_COUNTER = 'ac2'
    SERIAL_REUSE_COUNTER = 'ac3'

    # Additional user profile fields
    SERIAL_STREET1 = "ps1"
    SERIAL_STREET2 = "ps2"
    SERIAL_CITY = "pc"
    SERIAL_POSTAL_CODE = "ppc"
    SERIAL_REGION = "pr"
    SERIAL_TAX_ID = "pti"
    SERIAL_VAT = "pv"

    # OAUTH CREDENTIALS
    SERIAL_OAUTH_GITHUB_TOKEN = "oh"
    SERIAL_OAUTH_GOOGLE_TOKEN = "og"

    # MAX WORKSPACE SIZE
    SERIAL_MAX_WORKSPACE_SIZE = "m"

    EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"

    # Invited by
    SERIAL_INVITED_BY = "in"

    def __init__(self, brl_id):
        self.ID = brl_id
        self.password_timestamp = None
        self._encrypted_password = None
        # TODO: Confirmed email accounts? <= Only one at the moment, migrate active account
        # Basic fields
        self._email = None
        self.firstname = None
        self.lastname = None
        self.country = None
        self.description = None
        self.visible_email = False

        # Admin fields
        self.staff = False
        self.allow_mailing = True

        # Activation fields
        self.active = False
        self.confirmation_token = None
        self.joined_date = None
        self.confirmation_date = None

        # Workspace fields
        self.block_counter = 0
        self.blocks = {}  # {BRLBlock => (set(TAGS), "description", bytes_size)}
        self.administrators = Permissions()

        # Dict of brl_user => Num grants (block, hive or administrators)
        self.numeric_id = None
        self.social_accounts = {}

        # Achievements
        self.read_api_counter = 0
        self.publish_counter = 0
        self.reuse_counter = 0

        # Profile fields
        self.street_1 = ""
        self.street_2 = ""
        self.city = ""
        self.postal_code = ""
        self.region = ""
        self.tax_id = ""
        self.vat = ""

        # OAuth credentials
        self.oauth_google_token = None
        self.oauth_github_token = None

        # Max workspace size
        self.max_workspace_size = BII_MAX_USER_WORKSPACE_SIZE

        # Invited by
        self.invited_by = None

    def delete_block(self, brl_block):
        # we do a pop, just in case it doesn't work
        self.blocks.pop(brl_block)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, theemail):
        if theemail:
            import re
            if not re.match(User.EMAIL_REGEX, theemail):
                raise InvalidNameException("Invalid email")
        self._email = theemail

    @property
    def password(self):
        return None

    @password.setter
    def password(self, new_plain_password):
        if new_plain_password:
            if len(new_plain_password) < 6:  # TODO: Restrict with Regular expression?
                raise InvalidNameException("Password must have at least 6 characters")
        self._encrypted_password = encrypt(new_plain_password)
        self.password_timestamp = time.time()

    def valid_password(self, plain_password):
        return verify(plain_password, self._encrypted_password)

    @property
    def gravatar_email_hash(self):
        if self._email:
            return hashlib.md5(self.email.lower()).hexdigest()

    @property
    def full_name(self):
        return " ".join([self.firstname or "", self.lastname or ""])

    # ######### OLD WORKSPACE METHODS ###########
    def add_block(self, brl, tags=None, description=""):
        '''Adds a block to the user workspace'''
        tags = tags or set()

        if brl.owner != self.ID:
            raise ForbiddenException('Can not add not own block: %s %s' % (str(brl), self.ID))
        if brl in self.blocks:
            raise DuplicateBlockException('Block %s already exist for %s')
        matching = [x for x in self.blocks if brl.lower() == x.lower()]
        if matching:
            raise BiiException("You're trying to publish block named %s. There is "
                               "already a block named %s among your blocks" % (brl, matching[0]))
        # Add tags and description
        self.blocks[brl] = [set(tags), description, 0]  # 0 bytes
        block_id = self.numeric_id + self.block_counter
        self.block_counter += 1
        return block_id

    def add_block_tag(self, brl_block, tag):
        self.blocks[brl_block][0].add(tag)

    def remove_block_tag(self, brl_block, tag):
        self.blocks[brl_block][0].remove(tag)

    def get_block_tags(self, brl_block):
        return self.blocks[brl_block][0]

    def set_block_description(self, brl_block, new_description):
        self.blocks[brl_block][1] = new_description

    def get_block_description(self, brl_block):
        return self.blocks[brl_block][1]

    def add_block_size_bytes(self, brl_block, num_bytes):
        self.blocks[brl_block][2] += num_bytes

    def get_block_size_bytes(self, brl_block):
        return self.blocks[brl_block][2]

    @property
    def blocks_bytes(self):
        return sum(self.get_block_size_bytes(brl_block) for brl_block in self.blocks.keys())

    def fill_user_oauth_token(self, provider, token):
        if provider == "google":
            self.oauth_google_token = token
        elif provider == "github":
            self.oauth_github_token = token

    @property
    def ga_client_id(self):
        """Analytics client id"""
        aes_manager = AESEncryption(BII_AES_SECRET_KEY)
        client_id = aes_manager.encrypt(self.ID)
        return client_id

    #  END OLD WORKSPACE METHODS ###########

    def serialize(self):
        return Serializer().build(
                (self.SERIAL_ID_KEY, self.ID),
                (self.SERIAL_NUMERIC_ID, self.numeric_id),
                (self.SERIAL_ENCRYPTED_PASSWORD, self._encrypted_password),
                (self.SERIAL_PASSWORD_TIMESTAMP, self.password_timestamp),
                (self.SERIAL_FIRSTNAME, self.firstname),
                (self.SERIAL_LASTNAME, self.lastname),
                (self.SERIAL_COUNTRY, self.country),
                (self.SERIAL_DESCRIPTION, self.description),
                (self.SERIAL_EMAIL, self.email),
                (self.SERIAL_VISIBLE_EMAIL, self.visible_email),
                (self.SERIAL_ALLOW_MAILING, self.allow_mailing),
                (self.SERIAL_ACTIVE, self.active),
                (self.SERIAL_STAFF, self.staff),
                (self.SERIAL_JOINED_DATE, self.joined_date),
                (self.SERIAL_CONFIRMATION_DATE, self.confirmation_date),
                (self.SERIAL_CONFIRMATION_TOKEN, self.confirmation_token),
                # old workspace fields
                (self.SERIAL_MOD_COUNTER, self.block_counter),
                (self.SERIAL_BLOCKS, self.blocks),
                (self.SERIAL_ADMINISTRATORS, self.administrators),
                (self.SERIAL_SOCIAL_ACCOUNTS, self.social_accounts),
                (self.SERIAL_READ_API_COUNTER, self.read_api_counter),
                (self.SERIAL_PUBLISH_COUNTER, self.publish_counter),
                (self.SERIAL_REUSE_COUNTER, self.reuse_counter),
                # Additional profile fields
                (self.SERIAL_STREET1, self.street_1),
                (self.SERIAL_STREET2, self.street_2),
                (self.SERIAL_CITY, self.city),
                (self.SERIAL_POSTAL_CODE, self.postal_code),
                (self.SERIAL_REGION, self.region),
                (self.SERIAL_TAX_ID, self.tax_id),
                (self.SERIAL_VAT, self.vat),
                (self.SERIAL_OAUTH_GITHUB_TOKEN, self.oauth_github_token),
                (self.SERIAL_OAUTH_GOOGLE_TOKEN, self.oauth_google_token),
                (self.SERIAL_MAX_WORKSPACE_SIZE, self.max_workspace_size),
                # Invited by
                (self.SERIAL_INVITED_BY, self.invited_by),
                )

    @staticmethod
    def deserialize(doc):
        brl = BRLUser(doc[User.SERIAL_ID_KEY])
        user = User(brl)
        user._encrypted_password = doc[User.SERIAL_ENCRYPTED_PASSWORD]
        user.password_timestamp = doc.get(User.SERIAL_PASSWORD_TIMESTAMP, None)

        if User.SERIAL_NUMERIC_ID in doc:
            user.numeric_id = ID.deserialize(doc[User.SERIAL_NUMERIC_ID])

        # Profile fields
        user.firstname = doc.get(User.SERIAL_FIRSTNAME, None)
        user.lastname = doc.get(User.SERIAL_LASTNAME, None)
        user.country = doc.get(User.SERIAL_COUNTRY, None)
        user.description = doc.get(User.SERIAL_DESCRIPTION, None)
        user.email = doc.get(User.SERIAL_EMAIL, None)
        user.visible_email = doc.get(User.SERIAL_VISIBLE_EMAIL, 0) == 1
        user.allow_mailing = doc.get(User.SERIAL_ALLOW_MAILING, 0) == 1
        user.active = doc.get(User.SERIAL_ACTIVE, 0) == 1
        user.staff = doc.get(User.SERIAL_STAFF, 0) == 1
        user.joined_date = UtcDatetime.deserialize(doc.get(User.SERIAL_JOINED_DATE, None))
        user.confirmation_date = UtcDatetime.deserialize(doc.get(User.SERIAL_CONFIRMATION_DATE,
                                                                 None))
        user.confirmation_token = doc.get(User.SERIAL_CONFIRMATION_TOKEN, None)
        # Old workspace methods
        user.block_counter = doc.get(User.SERIAL_MOD_COUNTER, 0)
        blocks_data = doc.get(User.SERIAL_BLOCKS, {})
        user.blocks = DictDeserializer(BRLBlock, BlockMetaInfoDeserializer).deserialize(blocks_data)
        user.administrators = Permissions.deserialize(doc.get(User.SERIAL_ADMINISTRATORS, {}))
        social_accounts_doc = doc.get(User.SERIAL_SOCIAL_ACCOUNTS)
        user.social_accounts = DictDeserializer(str, SocialAccount).deserialize(social_accounts_doc)

        # Achievements
        user.read_api_counter = doc.get(User.SERIAL_READ_API_COUNTER, 0)
        user.publish_counter = doc.get(User.SERIAL_PUBLISH_COUNTER, 0)
        user.reuse_counter = doc.get(User.SERIAL_REUSE_COUNTER, 0)

        # Additional profile fields
        user.street_1 = doc.get(User.SERIAL_STREET1, "")
        user.street_2 = doc.get(User.SERIAL_STREET2, "")
        user.city = doc.get(User.SERIAL_CITY, "")
        user.postal_code = doc.get(User.SERIAL_POSTAL_CODE, "")
        user.region = doc.get(User.SERIAL_REGION, "")
        user.tax_id = doc.get(User.SERIAL_TAX_ID, "")
        user.vat = doc.get(User.SERIAL_VAT, "")

        # OAuth
        user.oauth_github_token = doc.get(User.SERIAL_OAUTH_GITHUB_TOKEN, None)
        user.oauth_google_token = doc.get(User.SERIAL_OAUTH_GOOGLE_TOKEN, None)

        # Max workspace size, default BII_MAX_USER_WORKSPACE_SIZE
        user.max_workspace_size = doc.get(User.SERIAL_MAX_WORKSPACE_SIZE,
                                          BII_MAX_USER_WORKSPACE_SIZE)

        # Invited by
        user.invited_by = doc.get(User.SERIAL_INVITED_BY, None)
        return user


class BlockMetaInfoDeserializer(object):
    '''Deserializes the tuple of values of each brlblock metainfo.
    (tags, description)'''
    @staticmethod
    def deserialize(data):
        if len(data) == 2:  # In case migration failed we insert 0 bytes to size
            data.append(0)
        return [SetDeserializer(unicode).deserialize(data[0]), unicode(data[1]), data[2]]
