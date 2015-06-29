from biicode.common.model.symbolic.reference import References
from biicode.common.deps.block_version_graph_builder import block_version_graph_build
from biicode.server.deps.compatibility_closure_builder import build_compatibility_closure
from biicode.server.deps.compatibility_closure import CompatibilityClosure
from biicode.common.model.symbolic.block_version_table import BlockVersionTable


class Hypothesis(object):
    def __init__(self, block_version, dep_dict, ref_translator, base_block_names, biiresponse):
        self.block_version = block_version
        self.dep_dict = dep_dict
        self._ref_translator = ref_translator
        self._base_block_names = base_block_names
        self._closure = None
        self._block_closure = None
        self._invalid = None
        self.biiresponse = biiresponse

    @property
    def closure(self):  # Lazy computation of closures
        if self._closure is None:
            missing = References()
            for targets in self.dep_dict.values():
                for target in targets:
                    missing[self.block_version].add(target.cell_name)
            self._closure = CompatibilityClosure(missing)
        return self._closure

    @property
    def invalid(self):
        if self._invalid is None:
            dep_block_names = self.block_closure.versions.keys()
            cycles = self._base_block_names.intersection(dep_block_names)
            if cycles:
                self.biiresponse.error('Version %s discarded, it has cycles to %s'
                                       % (self.block_version, cycles))
                self._invalid = True
            else:
                self._invalid = False
        return self._invalid

    @property
    def block_closure(self):  # Lazy computation of closures
        if self._block_closure is None:
            self._block_closure, _ = block_version_graph_build(self._ref_translator.get_dep_table,
                                                        [self.block_version],
                                                        BlockVersionTable())
        return self._block_closure

    def is_compatible(self, other):
        '''check if compatible with other Hypothesis object'''
        if self.invalid or other.invalid:
            return False
        graph_collision = self.block_closure.collision(other.block_closure)
        if not graph_collision:
            return True

        c1 = self.closure
        c2 = other.closure

        build_compatibility_closure(self._ref_translator, c1, graph_collision.nodes, self.block_closure)
        build_compatibility_closure(self._ref_translator, c2, graph_collision.nodes, other.block_closure)
        return c1.conflicts(c2) == 0

    def __repr__(self):
        return repr(self.block_version)
