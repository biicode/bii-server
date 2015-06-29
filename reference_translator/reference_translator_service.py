from biicode.common.model.symbolic.reference import ReferencedResources
from biicode.common.model.resource import Resource
from biicode.common.exception import NotInStoreException, ForbiddenException
from biicode.server.authorize import Security
from collections import defaultdict


class ReferenceTranslatorService(object):

    def __init__(self, store, auth_user):
        self._store = store
        self.security = Security(auth_user, self._store)

    def get_published_resources(self, references):
        result = ReferencedResources()
        for block_version, cell_names in references.iteritems():
            try:
                self.security.check_read_block(block_version.block)
                block = self._store.read_block(block_version.block)
                cell_ids = block.cells.get_ids(cell_names, block_version.time)
                content_ids = block.contents.get_ids(cell_names, block_version.time)
                cells = self._store.read_published_cells(cell_ids.values())
                contents = self._store.read_published_contents(content_ids.values())
                for name, rID in cell_ids.iteritems():
                    if name in content_ids:
                        cid = content_ids[name]
                        cid = contents[cid]
                    else:
                        cid = None  # Virtual resource
                    result[block_version][name] = Resource(cells[rID], cid)
            except (ForbiddenException, NotInStoreException):
                pass
        return result

    def get_published_min_refs(self, references):
        '''returns the minimum information required to perform a compatibility check for those
        references. This method is currently used just by CompatibilityClosureBuilder

        param references: {block_version: set(cell_names)}
        return: {block_version: {cell_name: (cell_id, content_id), root_id, [deps blockcellnames]}}
        '''
        result = defaultdict(dict)
        for block_version, cell_names in references.iteritems():
            try:
                self.security.check_read_block(block_version.block)
                block = self._store.read_block(block_version.block)
                cell_ids = block.cells.get_ids(cell_names, block_version.time)
                content_ids = block.contents.get_ids(cell_names, block_version.time)
                cells = self._store.read_min_cells(cell_ids.values())
                #This cells are {cellID: (rootID, dep_block_names)}
                for cell_name, cell_id in cell_ids.iteritems():
                    content_id = content_ids.get(cell_name)  # None if Virtual resource
                    root_id, deps = cells.get(cell_id, (None, None))
                    if root_id is not None:
                        result[block_version][cell_name] = ((cell_id, content_id), root_id, deps)
            except (ForbiddenException, NotInStoreException):
                pass

        return result

    def get_dep_table(self, block_version):
        self.security.check_read_block(block_version.block)
        block = self._store.read_block(block_version.block)
        table = block.dep_tables.find(block_version.time)
        return table
