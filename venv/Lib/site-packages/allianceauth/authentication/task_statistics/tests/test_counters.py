import datetime as dt

from django.test import TestCase
from django.utils.timezone import now

from allianceauth.authentication.task_statistics.counters import (
    dashboard_results, failed_tasks, retried_tasks, succeeded_tasks,
)


class TestDashboardResults(TestCase):
    def test_should_return_counts_for_given_time_frame_only(self):
        # given
        earliest_task = now() - dt.timedelta(minutes=15)

        succeeded_tasks.clear()
        succeeded_tasks.add(now() - dt.timedelta(hours=1, seconds=1))
        succeeded_tasks.add(earliest_task)
        succeeded_tasks.add()
        succeeded_tasks.add()

        retried_tasks.clear()
        retried_tasks.add(now() - dt.timedelta(hours=1, seconds=1))
        retried_tasks.add(now() - dt.timedelta(seconds=30))
        retried_tasks.add()

        failed_tasks.clear()
        failed_tasks.add(now() - dt.timedelta(hours=1, seconds=1))
        failed_tasks.add()

        # when
        results = dashboard_results(hours=1)
        # then
        self.assertEqual(results.succeeded, 3)
        self.assertEqual(results.retried, 2)
        self.assertEqual(results.failed, 1)
        self.assertEqual(results.total, 6)
        self.assertEqual(results.earliest_task, earliest_task)

    def test_should_work_with_no_data(self):
        # given
        succeeded_tasks.clear()
        retried_tasks.clear()
        failed_tasks.clear()
        # when
        results = dashboard_results(hours=1)
        # then
        self.assertEqual(results.succeeded, 0)
        self.assertEqual(results.retried, 0)
        self.assertEqual(results.failed, 0)
        self.assertEqual(results.total, 0)
        self.assertIsNone(results.earliest_task)
