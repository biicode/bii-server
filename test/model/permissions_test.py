import unittest
from mock import Mock
from biicode.common.model.brl.brl_user import BRLUser
from biicode.server.model.permissions.element_permissions import ElementPermissions


class PermissionsTest(unittest.TestCase):

    def setUp(self):
        self.owner = Mock()
        self.non_owner = Mock()

    def test_grant(self):
        perm = ElementPermissions(1, True)
        self.assertFalse(perm.read.is_granted("espartaco"))

        perm.read.grant("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))

        perm.read.grant("tiopepe")
        perm.write.grant("tiopepe")
        self.assertTrue(perm.write.is_granted("tiopepe"))
        self.assertTrue(perm.read.is_granted("tiopepe"))

        perm = ElementPermissions(1, True)
        perm.read.grant("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))
        perm.read.revoke("espartaco")
        self.assertFalse(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))

        #Revoke read, revoke all
        perm.write.grant("espartaco")
        perm.read.grant("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertTrue(perm.write.is_granted("espartaco"))
        perm.read.revoke("espartaco")
        self.assertFalse(perm.read.is_granted("espartaco"))
        self.assertTrue(perm.write.is_granted("espartaco"))

        #Revoke write, keep read
        perm.read.grant("espartaco")
        perm.write.revoke("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))
        perm.write.revoke("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))

        #Revoke read and write
        perm.write.grant("espartaco")
        self.assertTrue(perm.read.is_granted("espartaco"))
        self.assertTrue(perm.write.is_granted("espartaco"))
        perm.write.revoke("espartaco")
        perm.read.revoke("espartaco")
        self.assertFalse(perm.read.is_granted("espartaco"))
        self.assertFalse(perm.write.is_granted("espartaco"))

    def test_equals(self):
        perm1 = ElementPermissions(1, True)
        perm2 = ElementPermissions(1, False)
        self.assertNotEqual(perm1, perm2)

        perm1.is_private = False
        perm1.read.grant(BRLUser("laso"))
        perm2.read.grant(BRLUser("laso"))
        self.assertEqual(perm1, perm2)

        perm1.read.grant(BRLUser("laso2"))
        perm2.read.grant(BRLUser("laso3"))
        self.assertNotEqual(perm1, perm2)

        perm1.read.grant(BRLUser("laso3"))
        perm2.read.grant(BRLUser("laso2"))
        self.assertEqual(perm1, perm2)

        perm1.write.grant(BRLUser("laso"))
        self.assertNotEqual(perm1, perm2)

        perm2.write.grant(BRLUser("laso"))
        self.assertEqual(perm1, perm2)
