from biicode.common.exception import BiiStoreException
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.server.model.payment.user_subscription import UserSubscription,\
    FREE_PLAN_ID


class GenericServerStore(object):
    '''Implements common server store methods. Used with multi inheritance for support basic
    store methods read, write etc (MemStore and MongoStore).
    All object id attribute is a BRL'''

    PUBLISHED_CELL_ST = 'published_cell'
    PUBLISHED_CONTENT_ST = 'published_content'
    BLOCK_ST = 'block'
    USER_ST = 'user'
    COUNTERS_ST = 'counter'
    BLOCK_PERMISSIONS_ST = "block_permissions"
    USER_SUBSCRIPTION_ST = "user_subscription"

    def create_published_cells(self, values):
        '''Create published cells. Receives Cell objects'''
        return self.create_multi(values, GenericServerStore.PUBLISHED_CELL_ST)

    def create_published_contents(self, value):
        '''Create published contents. Receives a Content objects'''
        return self.create_multi(value, GenericServerStore.PUBLISHED_CONTENT_ST)

    def read_published_cells(self, res_ids):
        '''Reads published cells due a set of brls'''
        return self.read_multi(res_ids, GenericServerStore.PUBLISHED_CELL_ST)

    def read_published_contents(self, content_ids):
        '''Reads published contents due a set of brls'''
        return self.read_multi(content_ids, GenericServerStore.PUBLISHED_CONTENT_ST)

    def read_block(self, brl):
        '''Reads block by brl'''
        return self.read(brl, GenericServerStore.BLOCK_ST)

    def create_block(self, value, private=False):
        '''Insert a block. Value is a Block instance'''
        # Create default permissions
        self.create(ElementPermissions(value.ID, private), GenericServerStore.BLOCK_PERMISSIONS_ST)
        return self.create(value, GenericServerStore.BLOCK_ST)

    def read_user(self, brl):
        '''Reads user by brl'''
        return self.read(brl, GenericServerStore.USER_ST)

    def update_block(self, block):
        '''Update block. block is a Block instance'''
        return self.update(block, GenericServerStore.BLOCK_ST)

    def update_user(self, user):
        '''Update user. user is a User instance'''
        return self.update(user, GenericServerStore.USER_ST)

    def update_block_permissions(self, permissions):
        '''Updates a block permissions. permissions parameter is a Permission instance'''
        return self.update(permissions, GenericServerStore.BLOCK_PERMISSIONS_ST)

    def upsert_block_permissions(self, permissions):
        '''Upsert a block permissions. permissions parameter is a Permission instance'''
        return self.upsert(permissions, GenericServerStore.BLOCK_PERMISSIONS_ST)

    def delete_block(self, brl_block):
        self.delete_block_permissions(brl_block)
        return self.delete(brl_block, GenericServerStore.BLOCK_ST)

    def delete_block_permissions(self, brl_block):
        return self.delete(brl_block, GenericServerStore.BLOCK_PERMISSIONS_ST)

    def delete_published_cells(self, ids):
        '''Deletes edition cell due the brls'''
        return self.delete_multi(ids, GenericServerStore.PUBLISHED_CELL_ST)

    def delete_published_contents(self, ids):
        '''Deletes edition content due the brl'''
        return self.delete_multi(ids, GenericServerStore.PUBLISHED_CONTENT_ST)

    def create_user(self, user, numeric_id=None):
        '''Creates a user. user is a User instance.
        Params:
            user: user Object
            numeric_id: if specified, the numeric_id will be setted. Otherwise
                        it will be calculated due the user counter'''

        if not numeric_id:
            numeric_id = self.generate_user_id()

        user.numeric_id = numeric_id

        id_or_error = self.create(user, GenericServerStore.USER_ST, enable_update_if_current=True)
        if user.ID != id_or_error:
            raise BiiStoreException('Error (%s) creating user %s' % (id_or_error, user.ID))

        # Create user subscription
        user_subscription = UserSubscription(user.ID)
        user_subscription.plan_id = FREE_PLAN_ID
        self.create(user_subscription, GenericServerStore.USER_SUBSCRIPTION_ST)

    def read_user_subscription(self, brl_user):
        """Reads an user subscription"""
        return self.read(brl_user, GenericServerStore.USER_SUBSCRIPTION_ST)

    def update_user_subscription(self, user_subscription):
        '''Updates an user subscription'''
        return self.update(user_subscription, GenericServerStore.USER_SUBSCRIPTION_ST)

    def read_block_permissions(self, brl_block):
        ''' Gets Permission objects for a brl_block '''
        ret = self.read(brl_block, GenericServerStore.BLOCK_PERMISSIONS_ST)
        return ret

    # ************ Counts ***********
    def block_count(self):
        """Get the num of blocks"""
        return self.count(GenericServerStore.BLOCK_ST)

    def published_cell_count(self):
        """Get the num of published cells"""
        return self.count(GenericServerStore.PUBLISHED_CELL_ST)

    def user_count(self):
        """Get the num of users"""
        return self.count(GenericServerStore.USER_ST)
