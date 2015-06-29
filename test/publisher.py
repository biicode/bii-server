from biicode.server.api.bii_service import BiiService
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.exception import NotInStoreException
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.model.cells import SimpleCell
from biicode.common.model.dependency_set import DependencySet
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.content import Content
from biicode.common.model.version_tag import STABLE
from biicode.common.model.blob import Blob


class TestPublisher(object):
    def __init__(self, brl_user, store):
        self.brl_user = brl_user
        self.store = store
        self.service = BiiService(self.store, self.brl_user)

    def publish(self, brl_block, resource_info, version_tag=STABLE, dep_versions=None):
        """ make a simple publication of a single file named block_cell_name to block
        brl_block. If block does not exist, it creates it. It mantains coherence of root Ids
        for the find checks
        param resource_info: {cell_name: (blob, explicits)}
        """
        try:
            block = self.store.read_block(brl_block)
            version = BlockVersion(brl_block, len(block.deltas) - 1)
        except NotInStoreException:
            version = BlockVersion(brl_block, -1)

        publish_request = PublishRequest(version)
        publish_request.tag = version_tag

        block_name = brl_block.block_name
        for cell_name, (blob, dependencies) in resource_info.iteritems():
            if dependencies is not None:
                cell = SimpleCell(block_name + cell_name)
                if isinstance(dependencies, DependencySet):
                    cell.dependencies = dependencies
                else:
                    cell.dependencies.explicit.update([BlockCellName(d) for d in dependencies])
                publish_request.cells.append(cell)
            if blob is not None:
                blob = Blob(blob) if isinstance(blob, str) else blob
                publish_request.contents[cell_name] = Content(id_=None, load=blob)

        if isinstance(dep_versions, BlockVersion):
            dep_versions = [dep_versions]
        publish_request.deptable = BlockVersionTable(dep_versions)
        self.service.publish(publish_request)
