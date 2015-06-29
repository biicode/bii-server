from biicode.common.model.brl.brl_user import BRLUser
from biicode.server.model.user import User
from biicode.server.model.block import Block
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.server.utils.passlib_pbkdf2_sha512_wrapper import encrypt


class ModelCreator(object):
    def __init__(self, db):
        self._db = db

    def make_test_user(self):
        uid = self._db.generate_user_id()
        name = BRLUser('TestUser%d' % uid)
        user = User(name)
        user.password = 'password'
        user.active = True
        self._db.create_user(user, uid)
        return user

    def make_block(self, user=None, block=None):
        if user is None:
            user = self.make_test_user()
        brl_block = BRLBlock('%s/%s/TestBlock/master' % (user.ID, user.ID))
        mid = user.add_block(brl_block)
        self._db.update_user(user)
        if not block:
            block = Block(mid, brl_block)
        self._db.create_block(block)
        return block
