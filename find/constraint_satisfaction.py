from biicode.common.utils.bii_logging import logger
import copy


class History:
    def __init__(self, elem=None, var=-1, nVal=-1, depth=-1):
        self.elem = elem
        self.var = var
        self.nVal = nVal
        self.depth = depth


class BaseCSPElem(object):
    def is_compatible(self, other):
        raise NotImplementedError


class IterDeep(object):
    '''driver for iterative deepening search
       starts with first version for each hypothesis
       by default and iteratively adds one version'''

    END_ITER = -1
    NEXT_ITER = 0

    def __init__(self, csp, init_bounds=None, root_hyp=None):
        if init_bounds:
            self.__bounds = init_bounds
        else:
            self.__bounds = [1] * len(csp)     # only first version of each
        self.__csp_ref = csp
        self.__csp_cur = []
        if root_hyp:
            self.__root_hyp = root_hyp
        else:
            self.__root_hyp = None
        self.__solSet = []
        self.__isSolFound = False
        self.__numIter = 1

    @property
    def init_bounds(self):
        return self.__ini_bounds

    @init_bounds.setter
    def init_bounds(self, init):
        self.__init_bounds = init

    @property
    def is_solved(self):
        return self.__isSolFound

    @property
    def num_iter(self):
        return self.__numIter

    @property
    def csp_cur(self):
        return self.__csp_cur

    @property
    def csp_ref(self):
        return self.__csp_ref

    def __is_root_hyp_consistent(self):
        '''Determines block consistency for root hypothesis.
           At the moment not used'''
        for hyp in self.__root_hyp:
            if hyp.invalid:
                logger.debug('Root hyp invalid: {0}'.format(hyp))
                return False
        else:
            return True

    def start(self):
        ''' driver: returns True / [hypothesis sol] or False / None'''
        # check for root hyp consistency
        if self.__root_hyp:
            if not self.__is_root_hyp_consistent():
                self.__isSolFound = False
                return self.__isSolFound

        # configure and solve
        self.__solSet = []
        self.__isSolFound = False
        self.__init_csp()
        csp = CSPExact(self.__csp_cur, self.__root_hyp)
        #logger.debug(IterDeep.print_in_matrix_form(self.csp_cur))
        csp.solveCSP()
        while(not csp.isSolFound):
            if self.next_csp() == self.END_ITER:
                break
            csp = CSPExact(self.__csp_cur, self.__root_hyp)
            csp.solveCSP()
            self.__numIter += 1

        self.__isSolFound = csp.isSolFound
        if self.__isSolFound:
            self.__solSet = csp.getCompatibleSol()
            return  self.__isSolFound, self.__solSet
        else:
            return  self.__isSolFound, None

    def __init_csp(self):
        'builds root csp'
        for i, row in enumerate(self.__csp_ref):
            self.__csp_cur.append(row[: self.__bounds[i]])

    def next_csp(self):
        '''adds one hypothesis if possible to current csp'''
        ret_val = self.END_ITER
        for i, row in enumerate(self.__csp_cur):
            if len(row) < len(self.__csp_ref[i]):
                row.append(self.__csp_ref[i][len(self.__csp_cur[i])])
                ret_val = self.NEXT_ITER
        return ret_val

    def __repr__(self):
        'shows both csp in matrix form'
        ret_str = "sol_found: {0} + iter: {1}".format(self.__isSolFound,
                                                      self.__numIter)
        return ret_str

    @staticmethod
    def print_in_matrix_form(matrix):
        ret_str = ''
        for row in matrix:
            for elem in row:
                ret_str += str(elem)
            else:
                ret_str += '\n'
        ret_str += "\n"
        return ret_str


class CSPExact:
    MAX_NUM_SOL = 5
    LEAF_NODE = -1

    def __init__(self, csp_hyp, root_hyp):
        self.__csp = copy.copy(csp_hyp)
        if root_hyp:
            self.__root_hyp = root_hyp
        else:
            self.__root_hyp = None
        self.__nVAR = len(self.__csp)
        self.__nVAL = max(map(len, self.__csp))   # Maximum size of any row
        self.__nSteps = 0
        self.__depth_max = -1
        self.__nPropagations = 0
        self.__isSolFound = False
        self.__solSet = None                  # If compatible just one solution
        self.__arcConsistencyCheckOn = False
        self.__pathdict = None               # Path implemented as dic
        self.__history = None

    def __repr__(self):
        ret_str = ''
        for row in self.__csp:
            if row:
                for elem in row:
                    ret_str += str(elem)
                else:
                    ret_str += '\n'
            else:
                ret_str += 'Row None: possibly all invalid \n'
        ret_str += str(self.__solSet)
        ret_str += self.print_info()
        return ret_str

    def print_info(self):
        ret_str = '\n steps:{0} prop:{1} depth_max:{2} NVAR:{3}\n'.format(
                    self.__nSteps, self.__nPropagations,  self.__depth_max,
                    self.__nVAR)
        return ret_str

    @property
    def nVar(self):
        return self.__nVAR

    @nVar.getter
    def nVar(self):
        return self.__nVAR

    @property
    def arcConsistencyCheckOn(self):
        return self.__arcConsistencyCheckOn

    @arcConsistencyCheckOn.setter
    def arcConsistencyCheckOn(self, boolval):
        self.__arcConsistencyCheckOn = boolval

    @property
    def isSolFound(self):
        return self.__isSolFound

    @isSolFound.getter
    def isSolFound(self):
        return self.__isSolFound

    @property
    def nSteps(self):
        return self.__nSteps

    @nSteps.getter
    def nSteps(self):
        return self.__nSteps

    def getCompatibleSol(self):
        '''returns compatible list of hypothesis or None'''
        l = None
        if self.__isSolFound:
            l = []
            for t in self.__solSet[0]:
                x, y = t
                l.append(self.__csp[x][y])
        return l

    def __sizeList(self):
        '''list of sizes for each hypothesis. probably remove'''
        return max(map(len, self.__csp))

    def __initSearch(self):
        '''sets initial variable for the search;
           must be called after constructor'''
        if self.__nVAR == None or self.__csp == None:
            logger.error('invalid CSPExact')
            return -1        # possibly raise exception?
        else:
            self.__pathdict = {}
            self.__nSteps = 0
            self.__nPropagations = 0
            self.__depth_max = -1
            self.__isSolFound = False
            self.__solSet = []
            self.__history = []

    def preproc(self):
        '''propagates root_hyp: filters CSP elements
           incompatible with them (heavy proc. combine with ItDeep)
           If any root hyp is invalid the csp is incompatible.
           At the moment, not used'''
        for hyp in self.__root_hyp:
            if hyp.invalid:     # should not happen if launched from It.D.
                self.__isSolFound = False
                return
            for var in range(self.__nVAR):
                for val, elem in enumerate(self.__csp[var]):
                    if not elem.is_compatible(hyp):
                        self.__csp[var][val] = None

    def __propagate(self, var, depth, elemOut):
        '''filters a CSPExact variable and stores changes in history.
           Assumes variable nVar is unlabeled'''
        row = self.__csp[var]
        for i, elem in enumerate(row):
            if elem:
                if not elem.is_compatible(elemOut):
                    self.__nPropagations += 1
                    self.__history.append(History(elem, var, i, depth))
                    row[i] = None

    def __numberOfValues(self, var):
        '''number of non filtered values for variable nVar,
           assumed unlabeled'''
        nVal = 0
        for elem in self.__csp[var]:
            if elem != None:
                nVal += 1
        return nVal

    def __selectVar(self, depth):
        '''Decision heuristic for next variable assignment: most restricted
           (minimum number of values: ties broken first found)
           Prunes the search space if no candidate values are available for
           an unlabeled variable (returns LEAF_NODE) else returns new variable
           to expand'''
        retVar = 0
        minVal = self.__nVAL + 1
        for var in range(self.__nVAR):
            if not self.__isVarLabeled(var, depth):
                nVal = self.__numberOfValues(var)
                if nVal == 0:                 # PRUNE check no candidates
                    retVar = CSPExact.LEAF_NODE
                    break
                elif nVal < minVal:
                    minVal = nVal
                    retVar = var
        return retVar

    def __isVarLabeled(self, var, depth):
        '''Determines in current step if a variable is labeled.
           NOTE: Does not detect labeling in the current step'''
        if var in self.__pathdict:
            return True

    def solveCSP(self):
        '''search driver: returns TRUE is joint compatibility found'''
        self.__initSearch()
        if self.__root_hyp:
            self.preproc()
        self.__isSolFound = self.__expand(0)

        # Basic check of solution length
        if self.__isSolFound:
            if not self.__solSet or (len(self.__solSet[0]) != self.__nVAR):
                logger.error('Error in CSPExact: incorrect solution')
        return self.__isSolFound

    def __expand(self, depth):
        '''recursive search function driver'''
        self.__nSteps += 1

        # Early solution check
        if depth == self.__nVAR:
            self.__storeSol(depth)
            return True

        if self.__arcConsistencyCheckOn:
            # ArcConsistencyCheck, not implemented
            pass

        # Select variable
        nVarSel = self.__selectVar(depth)
        if nVarSel == CSPExact.LEAF_NODE:
            self.__storeSol(depth)
            return False                # Backtrack

        # Select value
        valCandidates = self.__csp[nVarSel]
        for index, elem in enumerate(valCandidates):
            if elem:                 # Decision heuristic, first non null
                if elem.invalid:
                    self.__csp[nVarSel] = None
                    continue
                else:
                    self.__pathdict[nVarSel] = index
                    self.__update(depth, elem)
                    if self.__expand(depth + 1) == True:
                        return True                    # Solution found
                    else:
                        self.__unupdate(depth)
                        del self.__pathdict[nVarSel]
        else:
            return False     # Chronological backtracking

    def __update(self, depth, elem):
        '''Bulk propagation operation over unlabeled variables'''
        for var in range(self.__nVAR):
            if not self.__isVarLabeled(var, depth + 1):   # inc. current depth
                self.__propagate(var, depth, elem)

    def __unupdate(self, depth):
        while(self.__history):
            h = self.__history.pop()
            if h.depth == depth:
                self.__csp[h.var][h.nVal] = h.elem
            else:
                self.__history.append(h)             # Replaces element
                break

    def __pathToSol(self, depth):
        '''stores new current best solution up to specified limit'''
        if len(self.__solSet) < CSPExact.MAX_NUM_SOL:
            tupleset = set({})
            for t in self.__pathdict.items():
                tupleset.add(t)
            else:
                self.__solSet.append(tupleset)

    def __storeSol(self, depth):
        '''stores sol if it is no worse than current champion
           (limited by MAX_NUM_SOL)'''
        if depth >= self.__depth_max:
            if depth > self.__depth_max:
                self.__depth_max = depth
                self.__solSet[:] = []
                logger.debug('new best solution found')
        self.__pathToSol(depth)

    def __isArcConsistent(self):
        ''' computes Arc-Consistency at current step'''
        pass
