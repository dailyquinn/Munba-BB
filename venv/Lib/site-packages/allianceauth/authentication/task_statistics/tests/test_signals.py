from unittest.mock import patch

from celery.exceptions import Retry

from django.test import TestCase, override_settings

from allianceauth.authentication.task_statistics.counters import (
    failed_tasks,
    retried_tasks,
    succeeded_tasks,
)
from allianceauth.authentication.task_statistics.signals import (
    reset_counters,
    is_enabled,
)
from allianceauth.eveonline.tasks import update_character


@override_settings(
    CELERY_ALWAYS_EAGER=True, ALLIANCEAUTH_DASHBOARD_TASK_STATISTICS_DISABLED=False
)
class TestTaskSignals(TestCase):
    fixtures = ["disable_analytics"]

    def setUp(self) -> None:
        succeeded_tasks.clear()
        retried_tasks.clear()
        failed_tasks.clear()

    def test_should_record_successful_task(self):
        # when
        with patch(
            "allianceauth.eveonline.tasks.EveCharacter.objects.update_character"
        ) as mock_update:
            mock_update.return_value = None
            update_character.delay(1)
        # then
        self.assertEqual(succeeded_tasks.count(), 1)
        self.assertEqual(retried_tasks.count(), 0)
        self.assertEqual(failed_tasks.count(), 0)

    def test_should_record_retried_task(self):
        # when
        with patch(
            "allianceauth.eveonline.tasks.EveCharacter.objects.update_character"
        ) as mock_update:
            mock_update.side_effect = Retry
            update_character.delay(1)
        # then
        self.assertEqual(succeeded_tasks.count(), 0)
        self.assertEqual(failed_tasks.count(), 0)
        self.assertEqual(retried_tasks.count(), 1)

    def test_should_record_failed_task(self):
        # when
        with patch(
            "allianceauth.eveonline.tasks.EveCharacter.objects.update_character"
        ) as mock_update:
            mock_update.side_effect = RuntimeError
            update_character.delay(1)
        # then
        self.assertEqual(succeeded_tasks.count(), 0)
        self.assertEqual(retried_tasks.count(), 0)
        self.assertEqual(failed_tasks.count(), 1)

    def test_should_reset_counters(self):
        # given
        succeeded_tasks.add()
        retried_tasks.add()
        failed_tasks.add()
        # when
        reset_counters()
        # then
        self.assertEqual(succeeded_tasks.count(), 0)
        self.assertEqual(retried_tasks.count(), 0)
        self.assertEqual(failed_tasks.count(), 0)


class TestIsEnabled(TestCase):
    @override_settings(ALLIANCEAUTH_DASHBOARD_TASK_STATISTICS_DISABLED=False)
    def test_enabled(self):
        self.assertTrue(is_enabled())

    @override_settings(ALLIANCEAUTH_DASHBOARD_TASK_STATISTICS_DISABLED=True)
    def test_disabled(self):
        self.assertFalse(is_enabled())
