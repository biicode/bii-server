#!/usr/bin/python
import unittest
from biicode.server.model.address_table import AddressTable
from biicode.server.model.time_base_map import TimeBaseMap, TimeBaseMapDeserializer
from biicode.server.model.block import Block
from biicode.server.model.permissions.element_permissions import ElementPermissions
from biicode.server.model.epoch.utc_datetime import UtcDatetime
from biicode.common.utils import serializer
from biicode.server.model.epoch.time_period import TimePeriod
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.utils.serializer import serialize
from biicode.common.model.id import ID
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.brl.cell_name import CellName


class SerializationTest(unittest.TestCase):
    '''serialization of objects of model ONLY in server'''

    def test_time_base_map(self):
        t = TimeBaseMap()
        mvt = BlockVersionTable([BlockVersion.loads("user/block: 3")])
        t.append(0, mvt)
        t.append(1, mvt)

        s = serialize(t)
        #print "TIME BASE:"+str(s)
        t2 = TimeBaseMapDeserializer(BlockVersionTable).deserialize(s)
        self.assertEqual(t, t2)

    def test_address_table(self):
        a = AddressTable(ID((1, 3)))
        a.create(CellName('f2.h'), ID((1, 3, 18)), 2)
        s = serialize(a)
        #print "S: " + str(s)
        b = AddressTable.deserialize(s, ID((1, 3)))
        #print "B: " + str(b)
        self.assertEqual(a, b)

    def test_block(self):
        m = Block(ID((1, 3)), BRLBlock('user/user/block/master', 1))
        #print "M: " + str(m)
        s = m.serialize()
        #print "S: " + str(s)
        m2 = Block.deserialize(s)
        #print "S: " + str(m2.serialize())
        #print "S2: " + str(m2)
        self.assertEqual(m, m2)

    def test_element_permissions(self):
        elem = ElementPermissions(BRLBlock("user/user/block/master"), True)
        elem.read.grant("pepe")
        elem.write.grant("juan")

        serial = elem.serialize()
        deserial = ElementPermissions.deserialize(serial)

        self.assertEqual(elem, deserial)

    def test_periodicity(self):
        elem = TimePeriod("YEAR", 2)
        serial = serializer.serialize(elem)
        elem2 = TimePeriod.deserialize(serial)
        self.assertEqual(elem, elem2)

    def test_utc_datetime(self):
        elem = UtcDatetime.get_current_utc_datetime()
        serial = elem.serialize()
        elem2 = UtcDatetime.deserialize(serial)
        self.assertEqual(elem, elem2)
