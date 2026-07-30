import datetime as dt

from pytz import utc

from django.test import TestCase
from django.utils.timezone import now

from allianceauth.authentication.task_statistics.event_series import (
    EventSeries,
)
from allianceauth.authentication.task_statistics.helpers import _RedisStub

MODULE_PATH = "allianceauth.authentication.task_statistics.event_series"


class TestEventSeries(TestCase):
    def test_should_add_event(self):
        # given
        events = EventSeries("dummy")
        # when
        events.add()
        # then
        result = events.all()
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], now(), delta=dt.timedelta(seconds=30))

    def test_should_add_event_with_specified_time(self):
        # given
        events = EventSeries("dummy")
        my_time = dt.datetime(2021, 11, 1, 12, 15, tzinfo=utc)
        # when
        events.add(my_time)
        # then
        result = events.all()
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], my_time, delta=dt.timedelta(seconds=30))

    def test_should_count_events(self):
        # given
        events = EventSeries("dummy")
        events.add()
        events.add()
        # when
        result = events.count()
        # then
        self.assertEqual(result, 2)

    def test_should_count_zero(self):
        # given
        events = EventSeries("dummy")
        # when
        result = events.count()
        # then
        self.assertEqual(result, 0)

    def test_should_count_events_within_timeframe_1(self):
        # given
        events = EventSeries("dummy")
        events.add(dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 15, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc))
        # when
        result = events.count(
            earliest=dt.datetime(2021, 12, 1, 12, 8, tzinfo=utc),
            latest=dt.datetime(2021, 12, 1, 12, 17, tzinfo=utc),
        )
        # then
        self.assertEqual(result, 2)

    def test_should_count_events_within_timeframe_2(self):
        # given
        events = EventSeries("dummy")
        events.add(dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 15, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc))
        # when
        result = events.count(earliest=dt.datetime(2021, 12, 1, 12, 8))
        # then
        self.assertEqual(result, 3)

    def test_should_count_events_within_timeframe_3(self):
        # given
        events = EventSeries("dummy")
        events.add(dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 15, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc))
        # when
        result = events.count(latest=dt.datetime(2021, 12, 1, 12, 12))
        # then
        self.assertEqual(result, 2)

    def test_should_clear_events(self):
        # given
        events = EventSeries("dummy")
        events.add()
        events.add()
        # when
        events.clear()
        # then
        self.assertEqual(events.count(), 0)

    def test_should_return_date_of_first_event(self):
        # given
        events = EventSeries("dummy")
        events.add(dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 15, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc))
        # when
        result = events.first_event()
        # then
        self.assertEqual(result, dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))

    def test_should_return_date_of_first_event_with_range(self):
        # given
        events = EventSeries("dummy")
        events.add(dt.datetime(2021, 12, 1, 12, 0, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 15, tzinfo=utc))
        events.add(dt.datetime(2021, 12, 1, 12, 30, tzinfo=utc))
        # when
        result = events.first_event(
            earliest=dt.datetime(2021, 12, 1, 12, 8, tzinfo=utc)
        )
        # then
        self.assertEqual(result, dt.datetime(2021, 12, 1, 12, 10, tzinfo=utc))

    def test_should_return_all_events(self):
        # given
        events = EventSeries("dummy")
        events.add()
        events.add()
        # when
        results = events.all()
        # then
        self.assertEqual(len(results), 2)

    def test_should_not_report_as_disabled_when_initialized_normally(self):
        # given
        events = EventSeries("dummy")
        # when/then
        self.assertFalse(events.is_disabled)

    def test_should_report_as_disabled_when_initialized_with_redis_stub(self):
        # given
        events = EventSeries("dummy", redis=_RedisStub())
        # when/then
        self.assertTrue(events.is_disabled)
