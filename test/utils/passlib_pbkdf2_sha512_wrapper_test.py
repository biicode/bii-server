import unittest
from biicode.server.utils.passlib_pbkdf2_sha512_wrapper import encrypt, verify


class Test(unittest.TestCase):

    def test_encrypt1(self):
        encrypted = encrypt("mandanga")
        self.assertTrue(verify("mandanga", encrypted))
        self.assertFalse(verify("", ""))


    def test_encrypt2(self):
        p1 = encrypt("prueba")
        assert verify("prueba", p1)

        assert verify("111111", "biicode$E4IwJiQEwJgzRkiJcc7Z2w$t7XxsRJrXnPeQmyfNtyNvh32xK2WTSiguCv5j9Nxh6A44lXTOoSjvHTfW2Vbdpi9YlOPypDo6Z1ssGnRizfk/g")

