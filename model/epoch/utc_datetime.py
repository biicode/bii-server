from delorean import Delorean
from pytz import all_timezones


class UtcDatetime(object):
    """Class for manage datetimes. The timezone is always internally in UTC. Its used for unify serialization
    and ease complexity of manage datetimes with timezones. Always use this class for datetime management"""

    def __init__(self, the_datetime, the_timezone):
        """the_datetime must be a datetime.datetime
           the_timezone is a String identifing timezone: EX: 'Europe/Madrid' 'UTC' See: all_timezones"""
        the_timezone = self._get_timezone_parameter(the_timezone)
        self._delorean = Delorean(datetime=the_datetime, timezone=the_timezone).shift("UTC")
        self._delorean.truncate('second')  # Truncate to second, its the precission of serialize

    @staticmethod
    def get_all_timezones():
        """All timezones available"""
        return all_timezones

    @staticmethod
    def get_current_utc_datetime():
        """Always call this method to get the current datetime.
           Return UrcDateTime"""
        delorean = Delorean()
        return UtcDatetime(delorean.datetime, "UTC")

    def datetime_in_timezone(self, the_timezone):
        """Gets the UTC timezone """
        the_timezone = self._get_timezone_parameter(the_timezone)
        tmp_delorean = Delorean(datetime=self._delorean.datetime)
        return tmp_delorean.shift(the_timezone).datetime

    def advance_in_time(self, periodicity):
        """Give us the future UtcDatetime traveling in time adding periodicity to self date"""
        if periodicity.period == "YEAR":
            return UtcDatetime(self._delorean.next_year(periodicity.frequency).datetime, "UTC")
        elif periodicity.period == "MONTH":
            return UtcDatetime(self._delorean.next_month(periodicity.frequency).datetime, "UTC")
        elif periodicity.period == "DAY":
            return UtcDatetime(self._delorean.next_day(periodicity.frequency).datetime, "UTC")

    def back_in_time(self, periodicity):
        """Give us the past UtcDatetime traveling in time substracting periodicity to self date"""
        if periodicity.period == "YEAR":
            return UtcDatetime(self._delorean.last_year(periodicity.frequency).datetime, "UTC")
        elif periodicity.period == "MONTH":
            return UtcDatetime(self._delorean.last_month(periodicity.frequency).datetime, "UTC")
        elif periodicity.period == "DAY":
            return UtcDatetime(self._delorean.last_day(periodicity.frequency).datetime, "UTC")

    @property
    def to_iso8601(self):
        return self.datetime_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    @property
    def datetime_utc(self):
        """datetime object in UTC"""
        return self._delorean.datetime

    @property
    def date_utc(self):
        """date object in UTC"""
        return self._delorean.date

    @staticmethod
    def deserialize(data):
        """deserialize model"""
        if data is None:
            return None
        return UtcDatetime(data, "UTC")

    def serialize(self):
        """serialize model
        NOTE: It serialize for pymongo datetime compatibility not for a string based interface like REST"""
        return self._delorean.datetime

    def __eq__(self, other):
        """equal method"""
        if self is other:
            return True
        return isinstance(other, self.__class__) \
            and self._delorean == other._delorean

    def __ne__(self, other):
        """not equal method"""
        return not self.__eq__(other)

    def __lt__(self, other):
        """< operation"""
        return self._delorean.datetime < other._delorean.datetime

    def __le__(self, other):
        """<= operation"""
        return self._delorean.datetime <= other._delorean.datetime

    def __gt__(self, other):
        """> operation"""
        return self._delorean.datetime > other._delorean.datetime

    def __ge__(self, other):
        """>= operation"""
        return self._delorean.datetime >= other._delorean.datetime

    def __sub__(self, other):
        """Returns a timedelta"""
        return self._delorean.datetime - other._delorean.datetime

    def _get_timezone_parameter(self, the_timezone):
        """Gets a valid timezone parameter or raise"""
        if the_timezone == "PST":  # Very common
            return "PST8PDT"
        if the_timezone not in self.get_all_timezones():
            raise ValueError("%s is not a valid timezone" % the_timezone)
        return the_timezone

    def __repr__(self):
        return "%s %s" % (self._delorean.naive(), self._delorean.timezone())
