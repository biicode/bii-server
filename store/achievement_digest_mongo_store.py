

class AchievementDigest(object):

    ID = 0
    SERIAL_NUM_READS = "c1"
    SERIAL_NUM_PUBLISH = "c2"
    SERIAL_NUM_REUSES = "c3"
    SERIAL_LAST_READS = "u1"
    SERIAL_LAST_PUBLISH = "u2"
    SERIAL_LAST_REUSES = "u3"

    def __init__(self):
        self.num_reads = 0
        self.num_publish = 0
        self.num_reuses = 0
        self._last_reads = []
        self._last_published = []
        self._last_reuses = []

    @staticmethod
    def deserialize(doc):
        digest = AchievementDigest()
        digest.num_reads = doc.get(AchievementDigest.SERIAL_NUM_READS, 0)
        digest.num_publish = doc.get(AchievementDigest.SERIAL_NUM_PUBLISH, 0)
        digest.num_reuses = doc.get(AchievementDigest.SERIAL_NUM_REUSES, 0)
        digest._last_reads = doc.get(AchievementDigest.SERIAL_LAST_READS, [])
        digest._last_published = doc.get(AchievementDigest.SERIAL_LAST_PUBLISH, [])
        digest._last_reuses = doc.get(AchievementDigest.SERIAL_LAST_REUSES, [])
        return digest

    @property
    def last_reads(self):
        tmp = [el for el in self._last_reads]  # copy
        tmp.reverse()
        return tmp

    @property
    def last_published(self):
        tmp = [el for el in self._last_published]  # copy
        tmp.reverse()
        return tmp

    @property
    def last_reuses(self):
        tmp = [el for el in self._last_reuses]  # copy
        tmp.reverse()
        return tmp


class AchievementDigestMongoStore(object):

    COLLECTION = "achievement_digest"
    DOCUMENT_ID = 1
    COUNTERS_DOC_KEY = "c"

    def __init__(self, mongo_server_store):
        self.server_store = mongo_server_store

    def read_achievement_digest(self):
        dbcol = self.server_store.db[self.COLLECTION]
        doc = dbcol.find_one({"_id": self.DOCUMENT_ID})
        return AchievementDigest.deserialize(doc) if doc else None

    def increment_total_read_counter(self, brl_user):
        """brl_user has readed from biicode for the first time, store it"""
        self._increment_counter(AchievementDigest.SERIAL_NUM_READS,
                                AchievementDigest.SERIAL_LAST_READS,
                                brl_user)

    def increment_total_publish_counter(self, brl_user):
        """brl_user has published from biicode for the first time, store it"""
        self._increment_counter(AchievementDigest.SERIAL_NUM_PUBLISH,
                                AchievementDigest.SERIAL_LAST_PUBLISH,
                                brl_user)

    def increment_total_reuse_counter(self, brl_user):
        """brl_user has published from biicode for the first time, store it"""
        self._increment_counter(AchievementDigest.SERIAL_NUM_REUSES,
                                AchievementDigest.SERIAL_LAST_REUSES,
                                brl_user)

    def _increment_counter(self, counter_field_name, user_list_field_name, brl_user):
        query = {"_id": self.DOCUMENT_ID}
        set_q = {"$inc": {counter_field_name: 1},
                 "$push": {user_list_field_name: brl_user}}
        self.server_store._update_collection(self.COLLECTION, query, set_q, True, None)

