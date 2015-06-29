from biicode.common.exception import BiiException, BiiStoreException, BiiRequestErrorException


class ControledErrorException(BiiRequestErrorException):  # For controlled errors
    pass


class BiiAuthorizationException(BiiException):
    pass


class BiiPendingTransactionException(BiiStoreException):
    pass


class MongoStoreException(BiiStoreException):
    pass


class MongoUpdateException(MongoStoreException):
    pass


class MongoNotCurrentObjectException(MongoUpdateException):
    pass


class MongoNotFoundUpdatingException(MongoUpdateException):
    pass


class MongoUpsertException(MongoUpdateException):
    pass


class DuplicateBlockException(BiiException):
    pass


class SubscriptionException(BiiException):
    pass


class InvalidCardException(SubscriptionException):
    pass


class MissingCardException(SubscriptionException):
    pass
