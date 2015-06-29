import unittest
from time import time

from biicode.server.model.address_table import AddressTable
from biicode.common.model.id import ID, UserID


class AddressTableTest(unittest.TestCase):
    def setUp(self):
        self.block_id = UserID(1) + 2  # ID(ID(1), 2)

    def test_name(self):
        table = AddressTable(self.block_id)
        size = 100
        step = 3
        for i in range(0, size):
            if i % step == 0:
                table.create("res1", self.block_id + (1000 + i), i)

        for i in range(0, size):
            id_ = table.get_id('res1', i)
            self.assertEqual(id_, self.block_id + (1000 + (i / step) * step))

    def test_speed(self):
        reps = 100
        table = AddressTable(self.block_id)
        size = 100
        step = 3
        for i in range(0, size):
            if i % step == 0:
                table.create("res1", self.block_id + (1000 + i), i)

        t = time()
        for r in range(0, reps):
            for i in range(0, size):
                _ = table.get_id('res1', i)
            # print i, ID
        avg_time = (time() - t) / (size * r)
        self.assertLess(avg_time, 60e-6)  # less than 30 microseconds

    def test_remove(self):
        table = AddressTable(self.block_id)

        table.create("r1", self.block_id + 123, 0)
        table.create("r2", self.block_id + 234, 0)

        table.create("r1", self.block_id + 1234, 1)
        table.delete("r2", 1)
        table.create("r3", self.block_id + 345, 1)

        self.assertEqual({'r1': self.block_id + 123,
                           'r2': self.block_id + 234},
                          table.get_all_ids(0))
        self.assertEqual({'r1': self.block_id + 1234,
                           'r3': self.block_id + 345},
                          table.get_all_ids(1))
        self.assertEqual({'r1': self.block_id + 1234,
                           'r3': self.block_id + 345}, table.get_all_ids(200))
