from biicode.server.utils.passlib_pbkdf2_sha512_wrapper import verify
from Crypto.Cipher import AES
import base64
from biicode.server.conf import BII_AES_SECRET_KEY


class Encryption(object):

    @staticmethod
    def validate_password(password, encrypted_password):
        return verify(password, encrypted_password)


class AESEncryption():
    # the block size for the cipher object; must be 16, 24, or 32 for AES
    # the character used for padding--with a block cipher such as AES, the value
    # you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
    # used to ensure that your value is always a multiple of BLOCK_SIZE
    BLOCK_SIZE = 32
    PADDING = '}'

    def __init__(self, secret_key):
        secret_len = len(secret_key)
        if secret_len != 16 and secret_len != 24 and secret_len != 32:
            raise ValueError("Key len must be 16, 24, or 32 for AES")
        # one-liner to sufficiently pad the text to be encrypted
        self.pad = lambda s: s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * self.PADDING
        # create a cipher object using the random secret
        self.cipher = AES.new(secret_key)

    def encrypt(self, string):
        # encode a string
        EncodeAES = lambda c, s: base64.b64encode(c.encrypt(self.pad(s)))
        encoded = EncodeAES(self.cipher, string)
        return encoded

    def decrypt(self, encoded_string):
        DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(self.PADDING)
        decoded = DecodeAES(self.cipher, encoded_string)
        return decoded
