from unittest.mock import patch
from django.test import TestCase

from allianceauth.crontab.models import CronOffset


class CronOffsetModelTest(TestCase):
    def test_cron_offset_is_singleton(self):
        """
        Test that CronOffset is indeed a singleton and that
        multiple calls to get_solo() return the same instance.
        """
        offset1 = CronOffset.get_solo()
        offset2 = CronOffset.get_solo()

        # They should be the exact same object in memory
        self.assertEqual(offset1.pk, offset2.pk)

    def test_default_values_random(self):
        """
        Test that the default values are set via random_default() when
        no explicit value is provided. We'll patch 'random.random' to
        produce predictable output.
        """
        with patch('allianceauth.crontab.models.random', return_value=0.1234):
            # Force creation of a new CronOffset by clearing the existing one
            CronOffset.objects.all().delete()

            offset = CronOffset.get_solo()  # This triggers creation

            # All fields should be 0.1234, because we patched random()
            self.assertAlmostEqual(offset.minute, 0.1234)
            self.assertAlmostEqual(offset.hour, 0.1234)
            self.assertAlmostEqual(offset.day_of_month, 0.1234)
            self.assertAlmostEqual(offset.month_of_year, 0.1234)
            self.assertAlmostEqual(offset.day_of_week, 0.1234)

    def test_update_offset_values(self):
        """
        Test that we can update the offsets and retrieve them.
        """
        offset = CronOffset.get_solo()
        offset.minute = 0.5
        offset.hour = 0.25
        offset.day_of_month = 0.75
        offset.month_of_year = 0.99
        offset.day_of_week = 0.33
        offset.save()

        # Retrieve again to ensure changes persist
        saved_offset = CronOffset.get_solo()
        self.assertEqual(saved_offset.minute, 0.5)
        self.assertEqual(saved_offset.hour, 0.25)
        self.assertEqual(saved_offset.day_of_month, 0.75)
        self.assertEqual(saved_offset.month_of_year, 0.99)
        self.assertEqual(saved_offset.day_of_week, 0.33)

    def test_str_representation(self):
        """
        Verify the __str__ method returns 'Cron Offsets'.
        """
        offset = CronOffset.get_solo()
        self.assertEqual(str(offset), "Cron Offsets")
