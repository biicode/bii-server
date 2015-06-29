
import copy
from collections import Iterator

# Warning: This class is unused, please do not remove

class Combinator(Iterator):

    def __init__(self, space):
        self.__space=space
        self.__initial = (0, ) * len(space)
        self.__open=[]
        self.__open.append(self.__initial)
        self.__discovered=set()
        self.__discovered.add(self.__initial)
        self.__level=0

    def next(self):
        if not self.__open:
            raise StopIteration

        indexes = self.__open.pop(0)
        s = sum(indexes)
        if s > self.__level:
            self.__level = s
            self.__discovered.clear()

        for i, row in enumerate(self.__space):
            if len(row) <= indexes[i]+1:
                continue
            aux = list(indexes)  # FIXME: Sure this is no pythonic
            aux[i] += 1
            childIndexes = copy.copy(tuple(aux))
            if childIndexes not in self.__discovered:
                self.__open.append(childIndexes)
                self.__discovered.add(childIndexes)

        result = []
        for i, row in enumerate(self.__space):
            result.append(self.__space[i][indexes[i]])

        return result

if __name__ == "__main__":
    space = [[0, 1, 2, 3, 4], [11, 12, 13], [21,22]]
    c = Combinator(space)
    for v in c:
        print 'value' + str(v)
