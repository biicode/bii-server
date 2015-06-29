import unittest
from biicode.server.test.find.generation_digraph import BiiGraph
import cProfile

from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.api.bii_service import BiiService
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.cells import SimpleCell
from biicode.common.model.id import ID
from biicode.common.model.version_tag import STABLE
from biicode.common.model.content import Content
from biicode.common.model.blob import Blob
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.dependency_set import DependencySet
from biicode.common.utils.bii_logging import logger
from biicode.common.find.finder_request import FinderRequest
from biicode.common.model.declare.cpp_declaration import CPPDeclaration
from biicode.common.find.policy import Policy
from biicode.server.test.store.mongo_test import TestWithMongo
from biicode.server.test.store.db_model_creator import ModelCreator
from biicode.common.publish.publish_request import PublishRequest
from biicode.common.api.ui import BiiResponse


class BaseDigraphTest(TestWithMongo):
    def _initUser(self):
        self.store = MongoServerStore(self.conn, self.__class__.__name__)
        self.mother = ModelCreator(self.store)
        self.testUser = self.mother.make_test_user()
        self.service = BiiService(self.store, self.testUser.ID)

    def _getBlockCellNames(self, dim):
        '''generates names from dim list'''
        bcns = [BlockCellName(self.testUser.ID + '/module%s/cell%s' % (i, i))
                for i in range(len(dim))]
        return bcns

    def _getBlockBRL(self, block_cell_name):
        return BRLBlock('{0}/{1}/master' .format(self.testUser.ID, block_cell_name.block_name))

    def _publishIndependentCell(self, block_cell_name, nVersions=10,
                                version_tag=None):
        '''publishes nVersions of each cell'''
        block_brl = self._getBlockBRL(block_cell_name)
        for v in range(0, nVersions):
            r = SimpleCell(block_cell_name)
            pack = PublishRequest(BlockVersion(block_brl, v - 1))
            pack.tag = version_tag if version_tag is not None else STABLE
            pack.cells.append(r)
            pack.deptable = BlockVersionTable()
            pack.contents[r.name.cell_name] = Content(id_=None, load=Blob('hola {0}'.format(v)))
            self.service.publish(pack)

    def _unresolvedDependencyRequest(self, unresolved_deps):
        request = FinderRequest()
        unresolved = set()
        for dep in unresolved_deps:
            unresolved.add(CPPDeclaration(dep))
        request.unresolved = unresolved
        request.policy = Policy.default()
        return request


class DigraphTest(BaseDigraphTest):
    DIM = [7] * 7  # [<num. vers. cell1>, <num. vers. cell2>, ...]
    pr = cProfile.Profile()

    def setUp(self):
        BaseDigraphTest.setUp(self)
        self._biigraph = BiiGraph(DigraphTest.DIM)
        self._biigraph.gen_compatible_graph()

    def testFinderCompatibleTest(self):
        ''' Generates compatible problem critical in the last two versions '''
        last_block = self._biigraph.get_num_blocks() - 1
        self._biigraph.make_independent(last_block, last_block - 1)
        t = self._biigraph._get_range_block(last_block - 2)
        self._biigraph.make_dependent(last_block, t[0])
        self._biigraph.make_dependent(last_block - 1,  t[0])
        self._publish_graph()

        # Solve
        request = self._unresolvedDependencyRequest(self.lbcn)
        result = self.service.find(request, BiiResponse())
        self.assertEqual(len(self.lbcn), len(result.resolved))

    def testFinderIncompatibleTest(self):
        ''' 'Generates incompatible problem with consistent closures '''
        last_block = self._biigraph.get_num_blocks() - 1
        self._biigraph.make_independent(last_block, last_block - 1)
        t = self._biigraph._get_range_block(last_block - 2)
        self._biigraph.make_dependent(last_block, t[0])
        self._biigraph.make_dependent(last_block - 1,  t[0] + 1)
        self._publish_graph()

        # Solve (profile code has been commented)
        request = self._unresolvedDependencyRequest(self.lbcn)
        #  DigraphTest.pr.enable()
        result = self.service.find(request, BiiResponse())
        #  DigraphTest.pr.disable()
        #  s = io.FileIO('C:/Users/pablo/Desktop/profile.txt','w')
        #  ps = pstats.Stats(DigraphTest.pr, stream=s)
        #  ps.strip_dirs().sort_stats(-1).print_stats()
        #  s.close()
        logger.debug('\n-------------Finder result-----------------------\n')
        logger.debug(result.resolved)
        self.assertEqual(0, len(result.resolved))

    def _publish_graph(self):
        self._initUser()
        self.lbcn = self._getBlockCellNames(DigraphTest.DIM)

        #publish independent cell
        self._publishIndependentCell(self.lbcn[0], DigraphTest.DIM[0])

        #publish dependent cells (all the rest)
        for block in range(1, len(DigraphTest.DIM)):
            self._publishDependentCell(block)

    def _publishDependentCell(self, block_id):
        low, high = self._biigraph._get_range_block(block_id)
        count = 0
        d = self.lbcn
        bcn = d[block_id]
        brl = self._getBlockBRL(bcn)
        for row in range(low, high + 1):
            r = SimpleCell(d[block_id])
            r.root = ID((0, bcn.block_name[-1:], 0))
            deps = DependencySet()
            dep_table = BlockVersionTable()
            for block in range(block_id):
                time = self._biigraph._get_dep_elem_offset(row, block)
                if time != -1:
                    deps.add_implicit(d[block])
                    dep_table[d[block].block_name] = \
                       BlockVersion(self._getBlockBRL(d[block]), time)
            r.dependencies = deps
            pack = PublishRequest(BlockVersion(brl, count - 1))
            pack.tag = STABLE
            count += 1
            pack.cells.append(r)
            pack.contents[r.name.cell_name] = Content(id_=None, load=Blob('hola {0}'.
                                                                format(r.name.cell_name)))
            pack.deptable = dep_table
            self.service.publish(pack)


if __name__ == "__main__":
    unittest.main()
