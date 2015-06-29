from biicode.common.settings.fixed_string import FixedString
from collections import namedtuple


class TimeUnit(FixedString):
    """Available periods"""
    values = {'YEAR', 'MONTH', 'DAY'}


class TimePeriod(namedtuple("Period", ['period', 'frequency'])):
    """Model representing a TimeUnit and a frequency (int)"""

    @staticmethod
    def deserialize(data):
        """deserialize model"""
        return TimePeriod(TimeUnit(data[0]), data[1])
