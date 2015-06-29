from biicode.common.utils.serializer import Serializer, ListDeserializer
from biicode.common.model.symbolic.block_version import BlockVersion


class LengthySerializedBlockVersion(BlockVersion):
    """Only extend BlockVersion serialization for be able to make complex querys with mongo"""

    SERIAL_CREATOR_KEY = "c"
    SERIAL_OWNER_KEY = "o"
    SERIAL_NAME_KEY = "n"
    SERIAL_BRANCH_KEY = "b"
    SERIAL_VERSION_KEY = "v"

    def serialize(self):
        ret = Serializer().build(
                 (self.SERIAL_CREATOR_KEY, self.block.creator),
                 (self.SERIAL_OWNER_KEY, self.block.owner),
                 (self.SERIAL_NAME_KEY, self.block_name.name),
                 (self.SERIAL_BRANCH_KEY, self.block.branch),
                 (self.SERIAL_VERSION_KEY, self.time)
        )
        return ret

    @staticmethod
    def deserialize(data):
        return LengthySerializedBlockVersion.loads("%s/%s(%s/%s):%i" % \
                                  (data[LengthySerializedBlockVersion.SERIAL_CREATOR_KEY],
                                   data[LengthySerializedBlockVersion.SERIAL_NAME_KEY],
                                   data[LengthySerializedBlockVersion.SERIAL_OWNER_KEY],
                                   data[LengthySerializedBlockVersion.SERIAL_BRANCH_KEY],
                                   data[LengthySerializedBlockVersion.SERIAL_VERSION_KEY]))


class ReverseDependency(object):
    '''Block versions which depend on a particular block version '''

    SERIAL_DEPS_ON_KEY = "d"

    def __init__(self, block_version, depends_on_version=None):
        if isinstance(block_version, BlockVersion):
            block_version = LengthySerializedBlockVersion(block_version.block,
                                                          block_version.time)

        self.version = block_version
        self._depends_on_version = []
        tmp = depends_on_version or []
        for dep in tmp:
            self.add_dependant_version(dep)

    @property
    def depends_on_version(self):
        return self._depends_on_version

    def add_dependant_version(self, block_version):
        tmp = LengthySerializedBlockVersion(block_version.block,
                                            block_version.time)

        self._depends_on_version.append(tmp)

    def serialize(self):
        ret = self.version.serialize()
        depends_on = Serializer().build(
                        (self.SERIAL_DEPS_ON_KEY, self._depends_on_version)
                    )
        ret.update(depends_on)
        return ret

    @staticmethod
    def deserialize(data):
        version = LengthySerializedBlockVersion.deserialize(data)
        tmp_des = ListDeserializer(LengthySerializedBlockVersion)
        depends_on_version = tmp_des.deserialize(data[ReverseDependency.SERIAL_DEPS_ON_KEY])
        ret = ReverseDependency(version)
        ret._depends_on_version = depends_on_version
        return ret

    def __repr__(self):
        return "%s => %s" % (self.version, self.depends_on_version)

    def __eq__(self, other):
        if self is other:
            return True
        return isinstance(other, self.__class__) \
            and self.version == other.version \
            and set(self._depends_on_version) == set(other._depends_on_version)

    def __ne__(self, other):
        return not self.__eq__(other)
