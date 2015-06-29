from biicode.common.utils.serializer import ListDeserializer
from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.exception import BiiException


class AlreadyGranted(BiiException):
    pass


class Permissions(set):

    def __init__(self, *args, **kwargs):
        super(Permissions, self).__init__(*args, **kwargs)

    @staticmethod
    def deserialize(doc):
        '''Deserializes the object from a list of three elements'''
        return Permissions(ListDeserializer(BRLUser).deserialize(doc))

    def grant(self, brl_user):
        if brl_user is None:  # Anonymous brl-user is None
            return
        if self.is_granted(brl_user):
            raise AlreadyGranted(brl_user)
        self.add(brl_user)

    def is_granted(self, brl_user):
        return brl_user and brl_user in self

    def revoke(self, brl_user):
        return self.discard(brl_user)
