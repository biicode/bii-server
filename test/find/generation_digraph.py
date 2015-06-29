'''
Created on 22/07/2013
Generates a joint compatible test given list dim with the number of versions
for each cell (in a single module)

Example: dim=[1,2,3]
Will generate:
  CellA (1 module 1 version
  CellB (1 module 2 versions)
  CellC (1 module 3 versions)
  C->B,A    B->A

Note:dim=[1,1,1,1..] will always produce a triangular matrix (bottom-left), a clique!

'''
from random import randint
from biicode.common.utils.bii_logging import logger


class BiiGraph(object):
    def __new__(cls, dim):
        if not dim or 0 in dim:
            print 'invalid dim'
            return None
        else:
            return super(BiiGraph, cls).__new__(cls, dim)

    def __init__(self, dim):
        self.__dim = dim
        s = sum(dim)
        self.__graph = [[0] * s for _ in range(s)]

    @property
    def graph(self):
        return self.__graph

    @property
    def dim(self):
        return self.__dim

    def get_num_rows(self):
        return sum(self.__dim)

    def get_num_blocks(self):
        return len(self.__dim)

    def get_block_size(self, block):
        return self.__dim[block]

    def _get_row_block(self, row):
        'returns 0 based block number'
        s = 0
        for block, dim in enumerate(self.__dim):
            s += dim
            if s > row:
                return block

    def _get_random_dep(self, block):
        low, high = self._get_range_block(block)
        return randint(low, high)    # Inclusive both ends

    def _fill_row_random(self, row):
        if row > 0:
            b = self._get_row_block(row) - 1
            if b >= 0:
                elem = self._get_random_dep(b)
                self.__graph[row][elem] = 1
                for block in reversed(range(b)):
                    low, high = self._get_range_block(block)
                    self.__graph[row][low:high + 1] = self.__graph[elem][low:high + 1]
                    if block > 0:
                        elem = self._get_dep_elem(elem, block)

    def _fill_row_consistently(self, row):
        block_row = self._get_row_block(row)
        elem = self._get_dep_elem(row, block_row - 1)
        for block in reversed(range(block_row - 1)):
            if elem == -1:
                elem = self._get_dep_elem(elem, block)
                continue
            low, high = self._getRangeBlock(block)
            self.__graph[row][low:high + 1] = self.__graph[elem][low:high + 1]
            if block > 0:
                elem = self._get_dep_elem(elem, block)

    def _get_range_block(self, block):
        low = sum(self.__dim[:block])
        high = sum(self.__dim[:block + 1]) - 1
        return(low, high)

    def gen_compatible_graph(self):
        '''generates joint compatible dependency bii-graph'''
        for row in range(sum(self.__dim)):
            self._fill_row_random(row)

    def _get_dep_elem_offset(self, elem, block):
        '''returns index of first element dependent in the block
           referred  to the block (or -1 if there is no dependency)'''
        low, high = self._get_range_block(block)
        try:
            elem = self.__graph[elem].index(1, low, high + 1)
        except ValueError:
            return -1
        return elem - low

    def _get_dep_elem(self, elem, block):
        '''returns a 0 based index of first element dependent in the block
           referred to the block (-1 if independent)'''
        low, high = self._get_range_block(block)
        try:
            new_elem = self.__graph[elem].index(1, low, high + 1)
        except ValueError:
            return -1
        return new_elem

    def make_independent(self, block_s, block_t):
        '''makes source block independent of target block'''
        low_s, high_s = self._get_range_block(block_s)
        low_t, high_t = self._get_range_block(block_t)
        for row in range(low_s, high_s + 1):
            self.__graph[row][low_t:high_t + 1] = [0] * self.get_block_size(block_t)

    def make_dependent(self, block_s, elem_t):
        '''makes source block depend on cell target elem'''
        block_t = self._get_row_block(elem_t)
        low_t, high_t = self._get_range_block(block_t)
        if block_t < block_s:
                low_s, high_s = self._get_range_block(block_s)
                for row_s in range(low_s, high_s + 1):
                    self.__graph[row_s][low_t: high_t + 1] = [0] * self.get_block_size(block_t)
                    self.__graph[row_s][elem_t] = 1
                    if block_t > 0:
                        elem = elem_t
                        for block in reversed(range(block_t)):
                            if elem == -1:                           # Independent
                                elem = self._get_dep_elem(elem, block)
                                continue
                            low, high = self._get_range_block(block)
                            self.__graph[row_s][low:high + 1] = self.__graph[elem][low:high + 1]
                            if block > 0:
                                elem = self._get_dep_elem(elem, block)
        else:
            logger.info('impossible to establish dependency')

    def __repr__(self):
        retstr = ''
        for row in self.__graph:
            for elem in row:
                retstr += str(elem)
            else:
                retstr += '\n'
        return retstr
