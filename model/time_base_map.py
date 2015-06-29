import bisect
from biicode.common.utils.serializer import ListDeserializer


class TimeBaseMap(tuple):
    '''
    Two lists, first of time, second of ID or BlockVersionTable or set or Renames
    '''
    def __new__(cls, data=None):
        if not data:
            obj = super(TimeBaseMap, cls).__new__(cls, ([], []))
        else:
            assert len(data) == 2, data
            obj = super(TimeBaseMap, cls).__new__(cls, (data[0], data[1]))
        return obj

    def pop_dev(self, time):
        old_time, _ = self.last()
        if old_time == time:
            self[0].pop()
            return self[1].pop()

    def last(self):
        try:
            return self[0][-1], self[1][-1]
        except IndexError:
            return None, None

    def append(self, time, item):
        self[0].append(time)
        self[1].append(item)

    def find(self, time):
        index = bisect.bisect_right(self[0], time)
        if self[0][index - 1] > time:
            return None
        return self[1][index - 1]

    def xrange(self, begin, end):
        for i, time in enumerate(self[0]):
            if begin <= time < end:
                yield self[1][i]


class TimeBaseMapDeserializer(object):

    def __init__(self, kls):
        self.kls = kls

    def deserialize(self, doc):
        times = doc[0]  # Not need to deserialize
        items = ListDeserializer(self.kls).deserialize(doc[1])
        return TimeBaseMap((times, items))
