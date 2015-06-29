from biicode.server.model.address_table import AddressTable
from biicode.server.model.time_base_map import TimeBaseMap
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.block_delta import BlockDelta
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.exception import PublishException
import time
from biicode.common.utils.bii_logging import logger
from biicode.common.utils.serializer import Serializer, ListDeserializer
from biicode.common.model.id import ID
from biicode.server.model.time_base_map import TimeBaseMapDeserializer
from biicode.common.model.renames import Renames
from biicode.common.model.version_tag import DEV


class Block(object):

    def __init__(self, numeric_id, brl_id):
        self._numeric_id = numeric_id
        self._id = brl_id
        self._cells_table = AddressTable(numeric_id)
        self._contents_table = AddressTable(numeric_id)
        self._deps_table = TimeBaseMap()
        self._renames = TimeBaseMap()
        self._deltas = []
        self._cell_count = 0
        self._content_count = 0

    def __repr__(self):
        result = []
        result.append('Block ' + repr(self._numeric_id) + repr(self._id))
        result.append(repr(self._cells_table))
        result.append(repr(self._contents_table))
        result.append(repr(self._deps_table))
        return '\n'.join(result)

    def all_ids(self):
        return self._cells_table.all_ids(), self._contents_table.all_ids()

    @property
    def ID(self):
        return self._id

    @property
    def numeric_id(self):
        return self._numeric_id

    @property
    def cells(self):
        return self._cells_table

    @property
    def contents(self):
        return self._contents_table

    @property
    def dep_tables(self):
        return self._deps_table

    @property
    def deltas(self):
        return self._deltas

    @property
    def cell_count(self):
        return self._cell_count

    @property
    def content_count(self):
        return self._content_count

    @property
    def last_delta(self):
        if not self.deltas:
            return None
        return self.deltas[len(self.deltas) - 1]

    def last_version(self):
        last_delta = len(self._deltas) - 1
        versiontag = self._deltas[last_delta].versiontag if last_delta >= 0 else None
        return BlockVersion(self._id, last_delta, versiontag)

    def last_version_cells(self):
        ''' Returns a dict {CellName => ID} with last version's cells '''
        return self.cells.get_all_ids(len(self._deltas) - 1)

    def get_renames(self, begin, end):
        '''Gets renames between given versions
        Paramenters:
            begin: int, excluded
            end: int, included
        Returns:
            Dict { old_cell_name => new_cell_name}
        '''
        renames = Renames()
        for r in self._renames.xrange(begin + 1, end + 1):
            renames. cat(r)
        return renames

    def add_publication(self, publish_request, commiter=None):
        logger.debug("--------------Requested publication---------\n %s" % repr(publish_request))

        current_time = len(self._deltas)
        delta = BlockDelta(publish_request.msg, publish_request.tag,
                           versiontag=publish_request.versiontag, date=time.time(),
                           origin=publish_request.origin,
                           commiter=commiter)

        # Check outdated
        target_time = publish_request.parent.time
        if target_time != current_time - 1:
            raise PublishException("Block %s outdated: %d < %d"
                                   % (publish_request.block_name, target_time, current_time - 1))

        # Promoting tag
        if not publish_request:
            if current_time > 0:
                old_delta = self._deltas[-1]
                if old_delta.tag < publish_request.tag:
                    self._deltas[-1] = delta
                    return [], [], [], []
            raise PublishException('Up to date, nothing to publish')

        # Handling dev
        if (current_time > 0 and self._deltas[current_time - 1].tag == DEV):
            if publish_request.parent_time != self._deltas[-1].date:
                raise PublishException("Concurrent modification, cannot publish, check diff and "
                                       "try again")
            current_time = current_time - 1
            self._deltas[-1] = delta
        else:
            self._deltas.append(delta)

        # DepTable
        self._deps_table.pop_dev(current_time)
        _, old_table = self._deps_table.last()
        if old_table != publish_request.deptable:
            self._deps_table.append(current_time, publish_request.deptable)

        contents = []
        cells = []
        dev_cell_ids = []
        dev_content_ids = []

        for name in publish_request.deleted:
            self._cells_table.delete(name, current_time)
            try:
                self._contents_table.delete(name, current_time)
            except KeyError:
                pass  # It was virtual

        for cell in publish_request.cells:
            old_id = self._cells_table.pop_dev(cell.name.cell_name, current_time)
            if old_id is not None:
                old_id = self._numeric_id + old_id[0]
                dev_cell_ids.append(old_id)

            id_ = self._numeric_id + self._cell_count
            self._cell_count += 1
            cell.ID = id_
            cells.append(cell)
            self._cells_table.create(cell.name.cell_name, cell.ID, current_time)

        for name, content in publish_request.contents.iteritems():
            old_id = self._contents_table.pop_dev(name, current_time)
            if old_id is not None:
                old_id = self._numeric_id + old_id[0]
                dev_content_ids.append(old_id)

            if content is not None:
                id_ = self._numeric_id + self._content_count
                self._content_count += 1
                content.ID = id_
                contents.append(content)
                self._contents_table.create(name, content.ID, current_time)
            else:
                self._contents_table.delete(name, current_time)  # Has become virtual

        for name, content_id in publish_request.contents_ids.iteritems():
            self._contents_table.create(name, content_id, current_time)

        # Renames
        self._renames.pop_dev(current_time)
        if publish_request.renames:
            self._renames.append(current_time, publish_request.renames)

        return (cells, contents, dev_cell_ids, dev_content_ids)

    def publish_datetime(self, time):
        '''Get the publication date of version "time"'''
        return self._deltas[time].date

    def __eq__(self, other):
        if self is other:
            return True
        return isinstance(other, self.__class__) \
            and self._numeric_id == other._numeric_id \
            and self._id == other._id \
            and self._cells_table == other._cells_table \
            and self._contents_table == other._contents_table \
            and self._deps_table == other._deps_table \
            and self._renames == other._renames \
            and self._deltas == other._deltas \
            and self._cell_count == other._cell_count \
            and self._content_count == other._content_count

    def __ne__(self, other):
        return not self.__eq__(other)

    SERIAL_ACCESS_KEY = 'a'
    SERIAL_NUMERIC_ID_KEY = 'n'
    SERIAL_ID_KEY = '_id'
    SERIAL_CELL_TABLE = 'rt'
    SERIAL_CONTENT_TABLE = 'ct'
    SERIAL_DEPS_TABLE = 'dt'
    SERIAL_RENAMES = 'm'
    SERIAL_DELTAS = 'dl'
    SERIAL_CELLS_COUNTER = 'i'
    SERIAL_CONTENT_COUNTER = 'j'

    def serialize(self):
        # TODO Add the rest of attributes
        assert isinstance(self._numeric_id, ID), self._numeric_id.__class__
        return Serializer().build(
                (self.SERIAL_ID_KEY, self._id),
                (self.SERIAL_NUMERIC_ID_KEY, self._numeric_id),
                (self.SERIAL_CELL_TABLE, self._cells_table),
                (self.SERIAL_CONTENT_TABLE, self._contents_table),
                (self.SERIAL_DEPS_TABLE, self._deps_table),
                (self.SERIAL_RENAMES, self._renames),
                (self.SERIAL_DELTAS, self._deltas),
                (self.SERIAL_CELLS_COUNTER, self._cell_count),
                (self.SERIAL_CONTENT_COUNTER, self._content_count)
        )

    @staticmethod
    def deserialize(doc):
        numeric_id = ID.deserialize(doc[Block.SERIAL_NUMERIC_ID_KEY])
        m = Block(brl_id=BRLBlock(doc[Block.SERIAL_ID_KEY]), numeric_id=numeric_id)
        m._cells_table = AddressTable.deserialize(doc[Block.SERIAL_CELL_TABLE], numeric_id)
        m._contents_table = AddressTable.deserialize(doc[Block.SERIAL_CONTENT_TABLE], numeric_id)
        m._deps_table = TimeBaseMapDeserializer(BlockVersionTable).deserialize(doc[Block.SERIAL_DEPS_TABLE])
        m._renames = TimeBaseMapDeserializer(Renames).deserialize(doc[Block.SERIAL_RENAMES])
        m._deltas = ListDeserializer(BlockDelta).deserialize(doc[Block.SERIAL_DELTAS])
        m._cell_count = int(doc[Block.SERIAL_CELLS_COUNTER])
        m._content_count = int(doc[Block.SERIAL_CONTENT_COUNTER])
        return m
