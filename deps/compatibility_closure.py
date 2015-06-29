from biicode.common.model.symbolic.reference import References


class CompatibilityClosure(object):
    '''Closure oriented to check compatibility between candidate versions in server'''

    def __init__(self, references=None):
        self._elements = {}   # {rootID: (cell_id, content_id), block_version, name }
        #The set of references that have to be explored yet, initially, the input references
        self.frontier = references or References()
        #Those references that were impossible to fetch, due to permissions or deletions
        self.broken = References()

    @property
    def references(self):
        r = References()
        for _, block_version, name in self._elements.itervalues():
            r[block_version].add(name)
        return r

    @property
    def block_cell_names(self):
        r = set()
        for _, block_version, name in self._elements.itervalues():
            r.add(block_version.block_name + name)
        return r

    def conflicts(self, other):
        '''pairwise compatibility between closures'''
        count = 0
        for root_id, (ids, _, _) in self._elements.iteritems():
            if root_id in other._elements:
                ids_other, _, _ = other._elements[root_id]
                # mapping must exist and values not equal for incompatibility
                if ids != ids_other:
                    count += 1
        return count

    def add_item(self, ids, root_id, block_version, name):
        #old_item = self._elements.get(root_id)
        #if old_item is not None:
        #    old_ids, _, _ = old_item
        #    if old_ids != ids:
        #        raise BiiException('Incompatibility here!')
        self._elements[root_id] = ids, block_version, name

    def __repr__(self):
        return str(self._elements)
