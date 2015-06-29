from biicode.common.store.mem_store import MemStore
from biicode.server.store.generic_server_store import GenericServerStore
from biicode.common.model.cells import SimpleCell


class MemServerStore(MemStore, GenericServerStore):

    def _init_holders(self):
        #NOTE: Do not rename dicts, they MUST match the method name
        self.published_cell = {}
        self.published_content = {}
        self.edition_cell = {}
        self.edition_content = {}
        self.hive = {}
        self.block = {}
        self.user = {}
        self.branches = {}
        self.counters = {"users": 0}
        self.block_permissions = {}
        self.hive_permissions = {}
        self.user_subscription = {}
        self.min_cells = {}  # {ID: (rootID, [deps_block_cell_names]
        self.content_sizes = {}  # For catching content_sizes

    def read_min_cells(self, ids):
        '''reads cells and cache only the minimum information necessary to compute compatibility
        checks. The reason is to save memory in the server.
        This funcion is only called by RefTranslator.get_published_min_refs, that is only called
        by CompatibilityClosureBuilder, only in FIND.
        Thus, FIND MUST always use a MemServerStore'''
        missing_ids = set(ids).difference(self.min_cells)
        cells = self._store.read_published_cells(missing_ids)
        for id_, cell in cells.iteritems():
            if isinstance(cell, SimpleCell):
                self.min_cells[id_] = (cell.root, list(cell.dependencies.targets))
            else:
                self.min_cells[id_] = (cell.root, list(cell.resource_leaves))
        result = {}
        for id_ in ids:
            try:
                result[id_] = self.min_cells[id_]
            except KeyError:
                pass
        return result

    def __getattr__(self, name):
        if self._store:
            return getattr(self._store, name)
        raise AttributeError('name %s' % name)

    ############ Get content sizes ################
    def read_content_sizes(self, content_ids):
        """Cached content sizes. self._store MUST EXIST"""
        missing_ids = set(content_ids).difference(self.content_sizes)
        content_sizes = self._store.read_content_sizes(missing_ids)
        # Assign to cached collection
        self.content_sizes.update(content_sizes)
        # return cached
        return {content_id: self.content_sizes[content_id] for content_id in content_ids}
