from biicode.common.find.finder_result import FinderResult
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.utils.bii_logging import logger
from heapq import heappush
import traceback
from copy import copy
from biicode.common.exception import NotInStoreException, ForbiddenException
from biicode.server.find.constraint_satisfaction import IterDeep
from biicode.server.authorize import Security
from biicode.server.reference_translator.reference_translator_service import \
                                                                        ReferenceTranslatorService
from biicode.server.find.hypothesis import Hypothesis
from biicode.common.model.brl.group_name import BranchName


class FindService(object):
    MAX_HYP = 10

    def __init__(self, store, auth_user):
        self._store = store
        self._auth_user = auth_user
        self.security = Security(self._auth_user, self._store)
        self.translator = ReferenceTranslatorService(self._store, self._auth_user)

    def find(self, request, biiout):
        '''
        Params:
            request: FinderRequest
            biiout: biiout
        Rerturns: FinderResult
        '''
        if not request:
            raise ValueError('The find request is empty, nothing to find')

        logger.debug('---------FinderRequest ------------\n%s' % str(request))
        result = FinderResult()
        # Copy unresolved and remove it if find the dependence
        result.unresolved = copy(request.unresolved)

        hypothesis = self._get_hypothesis(request, biiout)
        if not hypothesis:
            biiout.info("No block candidates found")
            return result

        biiout.info("Analyzing compatibility for found dependencies... ")
        '''# primitive combinator variant
        analyzer = CompatibilityAnalyzer(self._store, self._auth_user)
        analysis_result = analyzer.solve(hypothesis)

        # standard constraint variant
        csp = CSPExact(hypothesis, None)
        csp.solveCSP()
        analysis_result = csp.getCompatibleSol()
        logger.info(csp.print_info())'''

        # iterative deepening variant
        it = IterDeep(hypothesis, None, None)
        sol_found, analysis_result = it.start()
        if sol_found:
            logger.info("sol found: {0} iter".format(it.num_iter))

        if analysis_result is None:
            biiout.error("Can't find a compatible solution")
            return result

        self._update_result(analysis_result, request, result, biiout)
        if not result.unresolved:
            if result.resolved:
                biiout.info('All dependencies resolved')
            elif not result.updated:
                biiout.info('Everything was up to date')
        logger.debug('Result %s' % result)
        return result

    def _get_hypothesis(self, request, biiresponse):
        hypothesis = []
        if request.find:
            # group unresolved declarations by module
            possible_blocks = request.possible_blocks()
            logger.debug('Possible blocks %s' % possible_blocks)
            for block_name, decls in possible_blocks.items():
                hyp = self._compute_new(block_name, decls, request.policy,
                                        request.block_names, biiresponse)
                if len(hyp) > 0:  # Don't append []
                    hypothesis.append(hyp)

        existing_hypothesis = self._compute_existing(request, biiresponse)
        if len(existing_hypothesis) > 0:
            hypothesis.extend(existing_hypothesis)
        logger.debug('Hypothesis %s' % hypothesis)
        return hypothesis

    def _update_result(self, analysis_result, request, result, biiout):
        #existing = {version.block: version.time for version in request.existing}
        for elem in analysis_result:
            version = elem.block_version
            for declaration, refs in elem.dep_dict.iteritems():
                if declaration in request.unresolved:
                    biiout.debug("Resolved declaration %s" % str(declaration))
                    result.resolved[version][declaration] = refs
                elif version not in request.existing:
                    biiout.info("Block %s updated to version %s"
                                      % (version.block, version.time))
                    result.updated[version][declaration] = refs

            # Remove cells from finder response unresolved
            result.unresolved.difference_update(elem.dep_dict.keys())

    def _compute_existing(self, request, biiout):
        '''return a list of list of hypothesis for already defined (existing)
        dependencies'''
        result = []
        for block_version, deps in request.existing.iteritems():
            if request.update or request.downgrade or request.modify:
                hypothesis = self._compute_modify(block_version, deps, request, biiout)
            else:
                hypothesis = []
            hypothesis.append(Hypothesis(block_version, request.existing[block_version],
                                         self.translator, request.block_names, biiout))
            result.append(hypothesis)
        return result

    def _compute_modify(self, block_version, dependencies, request, biiout):
        '''
        Params:
            block_version: Version to which dependencies are currently resolved to
            dependencies: {Declaration: set(BlockCellName)}
            request: FinderRequest
        '''
        brl_block = block_version.block
        time = block_version.time

        # First, compute all block candidates that have to be considered
        block_candidates = {brl_block}

        # Remove those not wanted by our policy
        policy = request.policy
        block_candidates = policy.filter(block_candidates)

        current_block = self._store.read_block(brl_block)
        original_date = current_block.deltas[time].date
        delta_versions = self._filter_by_policy(block_candidates, policy, biiout,
                                                original_date, request)
        logger.debug("The heap is %s" % delta_versions)
        hypothesis = self._define_hypothesis(delta_versions, dependencies, request.block_names,
                                             biiout, block_version)
        return hypothesis

    def _match_declarations(self, decls, block, snap, cur_version, version):
        '''
        Params:
            decls: Current declarations for given block
            block: Block to match
            snap: dict {CellName => ID} for new version
            cur_version: Current BlockVersion that decls are resolved to
            version: New BlockVersion to evaluate
        Return:
            all_found: boolean
            names_total: set(BlockCellName)
            deps_dict: Dict {Declaration => set(BlockCellName)}
        '''
        all_found = True
        deps_dict = {}
        names_total = set()
        block_name = block.ID.block_name

        for decl in decls:
            matchable_names = snap.keys()
            renames = {}
            if cur_version:
                renames = block.get_renames(cur_version.time, version.time)
                matchable_names.extend(renames.keys())  # Adding old names so decls matches

            names = decl.match([block_name + name for name in matchable_names])
            names = set([n if n.cell_name in snap.keys()
                         else (block_name + renames[n.cell_name]) for n in names])  # Apply renames
            if names:
                # In case of renames here we will have a mismatch between declaration and cell_name
                # it will be corrected by client by updating declaration when it detects such
                # mismatch
                deps_dict[decl] = names
                names_total.update(names)
            else:
                all_found = False
                break
        return all_found, names_total, deps_dict

    def _define_hypothesis(self, delta_versions, decls, existing_block_names, biiresponse,
                           cur_version=None):
        '''
        Parameters:
            delta_versions: [(delta, block_version)], prioritized set of accepted hypothesis
            decls: {Declaration: set(BlockCellName)}
            existing_block_names = set(BlockName)
            cur_version: Current version that decls are resolved to

        Returns: list of hypothesis that match the required decls
        '''
        result = []

        #repeated = set()
        #previous = None
        for _, version in delta_versions:
            logger.debug('Analyzing hypothesis %s' % str(version))
            block = self._store.read_block(version.block)
            snap = block.cells.get_all_ids(version.time)
            #logger.debug('Current snap %s' % snap)

            all_found, names_total, deps_dict = self._match_declarations(decls, block, snap,
                                                                         cur_version, version)
            if not all_found:
                biiresponse.debug('Version %s discarded, only contains files for declarations %s'
                                  % (str(version), deps_dict.keys()))
                continue

            # Store the current IDs and dep table
            #snap_contents = block.contents.get_ids(version.time)
            #cell_ids = {snap[k.cell_name] for k in names_total}
            #content_ids = {snap_contents[k.cell_name] for k in names_total if
            #               k.cell_name in snap_contents}
            #dep_table = block.dep_tables.floor(version.time)
            #current = cell_ids, content_ids, dep_table
            # Only if the current option is different to the previous one
            # we dont want to check the same option twice
            #if previous != current and deps_dict:
            logger.debug('Building hypothesis for %s with %s' % (version, deps_dict))
            # logger.debug('ref_dict %s' % ref_dict)
            hyp = Hypothesis(version, deps_dict, self.translator, existing_block_names,
                             biiresponse)
            result.append(hyp)
            #previous = current
            # FIXME: now the limit of hypothesis is hardwired
            if len(result) >= FindService.MAX_HYP:
                break
        return result

    def _filter_by_policy(self, block_candidates, policy, biiresponse,
                          original_date=None, request=None):
        '''computes list of (block_delta, block_version) for each block candidate'''
        delta_versions = []
        for block_candidate in block_candidates:
            self.security.check_read_block(block_candidate)
            biiresponse.info("Block candidate: %s" % str(block_candidate))
            block = self._store.read_block(block_candidate)

            # from last to 0, backwards
            for num_version in range(len(block.deltas) - 1, -1, -1):
                tag = block.deltas[num_version].tag
                date = block.deltas[num_version].date
                if request:
                    if not request.downgrade and date <= original_date:
                        continue
                version = BlockVersion(block.ID, num_version)
                ev = policy.evaluate(version, tag)
                if ev:
                    heappush(delta_versions, ((-date, -num_version), version))
                    biiresponse.info("\tVersion %s (%s) valid" % (version, tag))
                else:
                    biiresponse.info("\tVersion %s (%s) discarded" % (version, tag))

        return delta_versions

    def _compute_new(self, block_name, decls, policy, existing_block_names, biiresponse):
        try:
            biiresponse.info("Looking for %s..." % block_name)
            # branches = self._store.read_tracks(block_name)
            # branches.get_blocks()
            block_candidates = [block_name + BranchName("%s/master" % block_name.user)]
            block_candidates = policy.filter(block_candidates)
            delta_versions = self._filter_by_policy(block_candidates, policy, biiresponse)
            logger.debug("The heap is %s" % delta_versions)
            result = self._define_hypothesis(delta_versions, decls,
                                             existing_block_names, biiresponse)
            return result
        except ForbiddenException:  # Propagate forbidden to client
            raise
        except NotInStoreException:
            biiresponse.warn("Can't find block candidate for: %s" % (str(block_name)))
            return []
        except Exception:
            biiresponse.error("Fatal error in server while reading %s" % block_name)
            logger.error(traceback.format_exc())
            return []
