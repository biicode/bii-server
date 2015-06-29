from biicode.server.model.time_base_map import TimeBaseMap
from biicode.common.model.id import ID
from biicode.common.utils.serializer import DictDeserializer
from biicode.common.model.brl.cell_name import CellName
from biicode.server.model.time_base_map import TimeBaseMapDeserializer


class AddressTable(dict):
    '''
    In this version, the last Integer of the ID is stored at each cell, or the full ID for tracking
    tested several approaches for efficiency, this seems to be pretty good
    with access times <1microsecond for 100 versions, all changing
    '''

    def __init__(self, block_id):
        self._block_id = block_id  # ID (user, block), transient

    def all_ids(self):
        result = set()
        for time_map in self.itervalues():
            for id_ in time_map[1]:
                # Only self IDs, external will not be deleted
                if id_ is not None and len(id_) == 1:  # Check if its a resourceID
                    result.add(self._block_id + id_[0])  # Get int resource value
        return result

    def last(self, name):
        try:
            return self[name].last()
        except KeyError:
            return None, None

    def pop_dev(self, name, time):
        try:
            return self[name].pop_dev(time)
        except KeyError:
            return None

    def delete(self, name, current_time):
        self[name].append(current_time, None)

    def create(self, name, item_id, current_time):
        if item_id.parent == self._block_id:
            id_ = ID((item_id[2], ))
        else:
            id_ = item_id
        return self.setdefault(name, TimeBaseMap()).append(current_time, id_)

    def get_id(self, name, time):
        '''Computes the resource in the time slot. Resolves for resources
           which do not have a explicit entry in time by taking the latest
           appearance before the time slot'''
        time_map = self.get(name)
        if time_map is None:
            return None
        return self._get_id(time_map, time)

    def get_ids(self, names, time):
        result = {}
        for name in names:
            id_ = self.get_id(name, time)
            if id_ is not None:
                result[name] = id_
        return result

    def get_all_ids(self, time):
        result = {}
        for name, time_map in self.iteritems():
            id_ = self._get_id(time_map, time)
            if id_ is not None:
                result[name] = id_
        return result

    def _get_id(self, time_based_map, time):
        id_ = time_based_map.find(time)
        if id_ is not None and len(id_) == 1:  # Check if its a resourceID
            return self._block_id + id_[0]  # Get int resource value
        return id_

    @staticmethod
    def deserialize(doc, block_id):
        m = AddressTable(block_id)
        tmp = DictDeserializer(CellName, TimeBaseMapDeserializer(ID)).deserialize(doc)
        m.update(tmp)
        return m
