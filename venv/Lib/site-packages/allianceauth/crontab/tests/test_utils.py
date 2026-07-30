# myapp/tests/test_tasks.py

import logging
from unittest.mock import patch
from django.test import TestCase
from django.db import ProgrammingError
from celery.schedules import crontab

from allianceauth.crontab.utils import offset_cron
from allianceauth.crontab.models import CronOffset

logger = logging.getLogger(__name__)


class TestOffsetCron(TestCase):

    def test_offset_cron_normal(self):
        """
        Test that offset_cron modifies the minute/hour fields
        based on the CronOffset values when everything is normal.
        """
        # We'll create a mock CronOffset instance
        mock_offset = CronOffset(minute=0.5, hour=0.5)

        # Our initial crontab schedule
        original_schedule = crontab(
            minute=[0, 5, 55],
            hour=[0, 3, 23],
            day_of_month='*',
            month_of_year='*',
            day_of_week='*'
        )

        # Patch CronOffset.get_solo to return our mock offset
        with patch('allianceauth.crontab.models.CronOffset.get_solo', return_value=mock_offset):
            new_schedule = offset_cron(original_schedule)

        # Check the new minute/hour
        # minute 0 -> 0 + round(60 * 0.5) = 30 % 60 = 30
        # minute 5 -> 5 + 30 = 35 % 60 = 35
        # minute 55 -> 55 + 30 = 85 % 60 = 25  --> sorted => 25,30,35
        self.assertEqual(new_schedule._orig_minute, '25,30,35')

        # hour 0 -> 0 + round(24 * 0.5) = 12 % 24 = 12
        # hour 3 -> 3 + 12 = 15 % 24 = 15
        # hour 23 -> 23 + 12 = 35 % 24 = 11 --> sorted => 11,12,15
        self.assertEqual(new_schedule._orig_hour, '11,12,15')

        # Check that other fields are unchanged
        self.assertEqual(new_schedule._orig_day_of_month, '*')
        self.assertEqual(new_schedule._orig_month_of_year, '*')
        self.assertEqual(new_schedule._orig_day_of_week, '*')

    def test_offset_cron_programming_error(self):
        """
        Test that if a ProgrammingError is raised (e.g. before migrations),
        offset_cron just returns the original schedule.
        """
        original_schedule = crontab(minute=[0, 15, 30], hour=[1, 2, 3])

        # Force get_solo to raise ProgrammingError
        with patch('allianceauth.crontab.models.CronOffset.get_solo', side_effect=ProgrammingError()):
            new_schedule = offset_cron(original_schedule)

        # Should return the original schedule unchanged
        self.assertEqual(new_schedule, original_schedule)

    def test_offset_cron_unexpected_exception(self):
        """
        Test that if any other exception is raised, offset_cron
        also returns the original schedule, and logs the error.
        """
        original_schedule = crontab(minute='0', hour='0')

        # Force get_solo to raise a generic Exception
        with patch('allianceauth.crontab.models.CronOffset.get_solo', side_effect=Exception("Something bad")):
            new_schedule = offset_cron(original_schedule)

        # Should return the original schedule unchanged
        self.assertEqual(new_schedule, original_schedule)
