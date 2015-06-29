import unittest
from biicode.server.model.reverse_dependency import (LengthySerializedBlockVersion,
    ReverseDependency)


class ReverseDependencyTest(unittest.TestCase):

    def serialize_and_deserialize_test(self):
        tmp = LengthySerializedBlockVersion.loads("creator/block(owner/branch):2")
        serial = tmp.serialize()

        tmp2 = LengthySerializedBlockVersion.deserialize(serial)
        self.assertEquals(tmp, tmp2)

        tmp = ReverseDependency(tmp, [tmp2, tmp])

        serial = tmp.serialize()

        self.assertEquals(serial[ReverseDependency.SERIAL_DEPS_ON_KEY][0] \
                                [LengthySerializedBlockVersion.SERIAL_NAME_KEY],
                                "block")

        tmp2 = ReverseDependency.deserialize(serial)
        self.assertEquals(tmp, tmp2)

        self.assertIsInstance(tmp2.depends_on_version[0], LengthySerializedBlockVersion)
