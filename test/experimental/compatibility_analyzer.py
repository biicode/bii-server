from combinator import Combinator
from biicode.common.utils.bii_logging import logger
import itertools


class CompatibilityAnalyzer(object):

    def __init__(self, store, authUser):
        self.__store = store
        self.__authUser = authUser

    def jointCompatibility(self, combination):
        # List<CSPSymbolicDependencySet> combination)
        return all([e1.is_compatible(e2) for e1, e2 in itertools.combinations(combination, 2)])

    # List<CSPSymbolicDependencySet>
    def solve(self, hypothesis):
        combinator = Combinator(hypothesis)

        while True:
            combination = combinator.getNext()
            if any(c.invalid for c in combination):
                break
            if not combination:
                #print "NO MORE POSSIBLE COMBINATIONS"
                break

            #print "Testing combination: " + str(combination)

            if self.jointCompatibility(combination):
                logger.debug("I FOUND A SOLUTION %s", combination)
                return combination
