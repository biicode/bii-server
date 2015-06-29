# HISTORICAL USE FOR:
# Django stores the password in DB with 128 characters. This is a "standard" for Django,
# because the password attribute of User class is defined in AbstractBaseUser class and
# this can't be override.

# We use 'biicode' as algorithm for Django. Django determines the hasher with the first
# parameter, the algorithm, in the hash (if it doesn't detect other algorithm before this).
# For this reason, we need replace the algorithm "biicode" for "$pbkdf2-sha512$12000$" and
# vice versa.

from passlib.handlers.pbkdf2 import pbkdf2_sha512

PBKDF2SHA512_HEADER = "$pbkdf2-sha512$12000$"
CUSTOM_HEADER = "biicode$"


def encrypt(password):
    '''encrypt a plain password'''
    enc = pbkdf2_sha512.encrypt(password, rounds=12000)
    enc = enc.replace(PBKDF2SHA512_HEADER, CUSTOM_HEADER, 1)
    return enc


def verify(password, encoded):
    '''verifies if encoded password correspond to plain password'''
    if encoded == "" or password == "" or encoded is None or password is None:
        return False
    encoded = encoded.replace(CUSTOM_HEADER, PBKDF2SHA512_HEADER, 1)
    #print encoded
    ver = pbkdf2_sha512.verify(password, encoded)
    return ver
