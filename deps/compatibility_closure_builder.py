#from biicode.common.utils.bii_logging import logger
from biicode.common.model.symbolic.reference import References
from biicode.common.model.symbolic.block_version_table import BlockVersionTable


def _compute_frontier(missing_dict, restricted_versions, full_graph, retrieved, open_frontier):
    frontier = References()
    for block_version, targets in missing_dict.iteritems():
        neighbours = BlockVersionTable(full_graph.neighbours(block_version))
        for target in targets:
            if target.block_name != block_version.block_name:
                other_version = neighbours.get(target.block_name)
                if other_version not in restricted_versions:
                    open_frontier[other_version].add(target.cell_name)
            else:
                other_version = block_version
            if other_version in restricted_versions and target.cell_name not in retrieved[other_version]:
                frontier[other_version].add(target.cell_name)
    return frontier


def build_compatibility_closure(api, closure, restricted_versions, full_graph):
    """ Builds compatibility closure for references

        Args:
            api (biicode.server.reference_translator.reference_translator_service.\
                                                            ReferenceTranslatorService):
                MUST implement get_dep_table and get_published_min_refs
            references: missing references to fetch and add to closure
    """
    retrieved = References()  # Accumulates all references retrieved

    # define the frontier to be taken into account to expand, and update it removing those elements
    frontier = References()
    for version, cell_names in closure.frontier.items():
        if version in restricted_versions:
            frontier[version] = cell_names
            del closure.frontier[version]

    while frontier:
        #logger.debug("Missing to fetch: %s" % str(references))
        min_cells = api.get_published_min_refs(frontier)
        # min_cells are {block_version: {cell_name: ((cell_id, content_id), root_id, deps)}
        #From what has been retrieved, add to closure, and store in missing_dict all the references
        # to be translated
        missing_dict = References()
        for block_version, cell_dict in min_cells.iteritems():
            for cell_name, ((cell_id, content_id), root_id, deps) in cell_dict.iteritems():
                retrieved[block_version].add(cell_name)
                closure.add_item((cell_id, content_id), root_id, block_version, cell_name)
                if deps:
                    missing_dict[block_version].update(deps)

        # Account for deletions, if something was not obtained from api (deleted or changed
        # permissions) it will be a missing reference in our closure
        for version, names in frontier.iteritems():
            broken_names = names.difference(min_cells.get(version, []))
            if broken_names:
                closure.broken[version].update(broken_names)

        # now, the references are the new ones
        frontier = _compute_frontier(missing_dict, restricted_versions, full_graph, retrieved,
                                     closure.frontier)
