import unittest
from biicode.server.find.constraint_satisfaction import BaseCSPElem, CSPExact
from biicode.common.utils.bii_logging import logger


class CSPElem(BaseCSPElem):

    def __init__(self, value, is_invalid=False):
        self.value = value
        self.invalid = is_invalid   # If True cannot make part of sol

    def is_compatible(self, other):
        return (False) if (self.value == -2 and other.value == -1) or \
                (self.value == -1 and other.value == -2) else True

    def __repr__(self):
        return '{0} '.format(self.value)


class CSPTest(unittest.TestCase):
    NVAR = 5
    NVAL = 5

    def setUp(self):
        self.__csp = [[None for j in range(CSPTest.NVAL)] for i in range(CSPTest.NVAR)]
        for i in range(CSPTest.NVAR):
            for j in range(CSPTest.NVAL):
                self.__csp[i][j] = CSPElem(i)

    def testInitialCSPElem(self):
        ''' initial root_hyp makes csp incompatible'''
        for i in range(CSPTest.NVAL):
            self.__csp[CSPTest.NVAR - 2][i].value = -1
            self.__csp[CSPTest.NVAR - 1][i].value = 8
        solver = CSPExact(self.__csp, [CSPElem(-2, False)])

        solFound = solver.solveCSP()
        logger.debug(solver)
        self.assertEqual(False, solFound)

    def testInitialInvalidCSPElem(self):
        '''invalid root_hyp does not affect incompatibility'''
        for i in range(CSPTest.NVAL):
            self.__csp[CSPTest.NVAR - 2][i].value = -1
            self.__csp[CSPTest.NVAR - 1][i].value = 8
        solver = CSPExact(self.__csp, [CSPElem(-2, True)])

        solFound = solver.solveCSP()
        logger.debug(solver)
        self.assertEqual(True, solFound)

    def testWorstCaseSimpleCSP(self):
        '''incompatible problem last hyp'''
        for i in range(CSPTest.NVAL):
            self.__csp[CSPTest.NVAR - 2][i].value = -1
            self.__csp[CSPTest.NVAR - 1][i].value = -2
        solver = CSPExact(self.__csp, None)
        solFound = solver.solveCSP()
        logger.debug(solver)
        self.assertEqual(False, solFound)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'CSPTest.testName']
    unittest.main()
