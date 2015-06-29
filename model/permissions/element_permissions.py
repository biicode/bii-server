from biicode.common.utils.serializer import Serializer
from biicode.server.model.permissions.permissions import Permissions


class ElementPermissions(object):
    '''Model common permissions for block and hive.'''

    def __init__(self, ID, private=False):
        self.ID = ID
        self.is_private = private
        self.read = Permissions()
        self.write = Permissions()

    @staticmethod
    def deserialize(doc):
        '''Deserializes the object from a list of 4 elements'''
        permi = ElementPermissions(doc[ElementPermissions.SERIAL_ID],
                                   doc[ElementPermissions.SERIAL_IS_PRIVATE])
        permi.read = Permissions.deserialize(doc[ElementPermissions.SERIAL_READ])
        permi.write = Permissions.deserialize(doc[ElementPermissions.SERIAL_WRITE])
        return permi

    SERIAL_ID = "_id"
    SERIAL_IS_PRIVATE = "p"
    SERIAL_READ = "r"
    SERIAL_WRITE = "w"
    SERIAL_OWNER = "u"

    def serialize(self):
        '''Serialize the object to a 4 element tuple'''
        res = Serializer().build(
            (ElementPermissions.SERIAL_ID, self.ID),  # BRLBlock
            (ElementPermissions.SERIAL_IS_PRIVATE, self.is_private),
            (ElementPermissions.SERIAL_READ, self.read),
            (ElementPermissions.SERIAL_WRITE, self.write)
        )
        return res

    def __eq__(self, other):
        '''Is equals?'''
        if self is other:
            return True
        return isinstance(other, self.__class__) \
            and self.ID == other.ID \
            and self.is_private == other.is_private \
            and self.read == other.read \
            and self.write == other.write

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "Block: %s\nPrivate: %s\nRead: %s\nWrite: %s" % (self.ID,
                                                                self.is_private,
                                                                 self.read, self.write)
