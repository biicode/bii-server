import unittest
from biicode.server.model.epoch.utc_datetime import UtcDatetime
import datetime
from biicode.server.model.epoch.time_period import TimePeriod


class UtcDateTimeTest(unittest.TestCase):
    """Test for utc_datetime_test class"""

    def testCreation(self):
        self.assertRaises(ValueError, UtcDatetime, "asdasd", 213)
        utc_datetime = UtcDatetime.get_current_utc_datetime()

        # Convert to pacific datatime
        pacific_standart_datetime = utc_datetime.datetime_in_timezone("PST")

        # Construct from pacific datetime
        other_utc_datetime = UtcDatetime(pacific_standart_datetime, "PST")

        # Must be the same!! its the same with different zone!!
        self.assertEqual(utc_datetime, other_utc_datetime)

        # Datetimes are also equals, different zone, same time
        self.assertEqual(pacific_standart_datetime, utc_datetime.datetime_utc)

    def testTimeTravel(self):
        one_datetime = datetime.datetime(2013, 11, 20, 13, 0, 6)
        utc_datetime = UtcDatetime(one_datetime, "Europe/Madrid")

        new_datetime = utc_datetime.advance_in_time(TimePeriod("YEAR", 34))

        # Test not destructive
        self.assertEqual(utc_datetime, UtcDatetime(one_datetime, "Europe/Madrid"))

        # Test we are in 2047, Maybe Madrid it's then Olympic city? LOL!
        expected_datetime = UtcDatetime(datetime.datetime(2047, 11, 20, 13, 0, 6), "Europe/Madrid")
        self.assertEqual(new_datetime, expected_datetime)

        # Test advance day
        new_datetime = utc_datetime.advance_in_time(TimePeriod("DAY", 1))
        expected_datetime = UtcDatetime(datetime.datetime(2013, 11, 21, 13, 0, 6), "Europe/Madrid")
        self.assertEqual(new_datetime, expected_datetime)

        # Test advance 3 month
        new_datetime = utc_datetime.advance_in_time(TimePeriod("MONTH", 3))
        expected_datetime = UtcDatetime(datetime.datetime(2014, 2, 20, 13, 0, 6), "Europe/Madrid")
        self.assertEqual(new_datetime, expected_datetime)

        # Test back 31 years, 9 months and 19 days
        new_datetime = utc_datetime.back_in_time(TimePeriod("YEAR", 31))
        new_datetime = new_datetime.back_in_time(TimePeriod("MONTH", 7))
        new_datetime = new_datetime.back_in_time(TimePeriod("DAY", 19))
            # Cool! its my birthdate!! (NOTE: It diff one hour because there \
            # is a local hour change on Spain from April to November)
        expected_datetime = UtcDatetime(datetime.datetime(1982, 04, 1, 14, 0, 6), "Europe/Madrid")
        self.assertEqual(new_datetime, expected_datetime)

    def test_compare(self):

        one_datetime = datetime.datetime(2013, 11, 20, 13, 0, 6)
        utc_datetime = UtcDatetime(one_datetime, "Europe/Madrid")

        new_datetime = utc_datetime.back_in_time(TimePeriod("YEAR", 31))

        self.assertTrue(utc_datetime > new_datetime)
        self.assertFalse(utc_datetime < new_datetime)
        self.assertTrue(utc_datetime >= new_datetime)
        self.assertFalse(utc_datetime <= new_datetime)

        new_datetime = utc_datetime.advance_in_time(TimePeriod("YEAR", 31))

        self.assertFalse(utc_datetime > new_datetime)
        self.assertTrue(utc_datetime < new_datetime)
        self.assertFalse(utc_datetime >= new_datetime)
        self.assertTrue(utc_datetime <= new_datetime)
