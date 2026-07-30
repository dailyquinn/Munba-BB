from unittest.mock import patch

from django.test import TestCase
from allianceauth.tests.auth_utils import AuthUtils

from ..models import Notification


MODULE_PATH = 'allianceauth.notifications.models'


class TestUserNotify(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('magic_mike')
        AuthUtils.add_main_character(
            cls.user,
            'Magic Mike',
            '1',
            corp_id='2',
            corp_name='Pole Riders',
            corp_ticker='PRIDE',
            alliance_id='3',
            alliance_name='RIDERS'
        )

    @patch(MODULE_PATH + '.Notification.objects.invalidate_user_notification_cache')
    def test_save_will_invalidate_cache(self, mock_invalidate_user_notification_cache):
        obj = Notification.objects.notify_user(self.user, 'dummy')
        self.assertTrue(Notification.objects.filter(pk=obj.pk).exists())
        self.assertEqual(mock_invalidate_user_notification_cache.call_count, 1)

    @patch(MODULE_PATH + '.Notification.objects.invalidate_user_notification_cache')
    def test_delete_will_invalidate_cache(
        self, mock_invalidate_user_notification_cache
    ):
        obj = Notification.objects.notify_user(self.user, 'dummy')
        obj.delete()
        self.assertFalse(Notification.objects.filter(pk=obj.pk).exists())
        self.assertEqual(mock_invalidate_user_notification_cache.call_count, 2)

    def test_can_view(self):
        obj = Notification.objects.notify_user(self.user, 'dummy')
        self.assertFalse(obj.viewed)
        obj.mark_viewed()
        obj.refresh_from_db()
        self.assertTrue(obj.viewed)

    def test_can_set_level(self):
        obj = Notification.objects.notify_user(self.user, 'dummy', level='info')
        obj.set_level('ERROR')
        obj.refresh_from_db()
        self.assertEqual(obj.level, 'danger')

        obj.set_level('CRITICAL')
        obj.refresh_from_db()
        self.assertEqual(obj.level, 'danger')

        obj.set_level('WARN')
        obj.refresh_from_db()
        self.assertEqual(obj.level, 'warning')

        obj.set_level('INFO')
        obj.refresh_from_db()
        self.assertEqual(obj.level, 'info')

        obj.set_level('DEBUG')
        obj.refresh_from_db()
        self.assertEqual(obj.level, 'success')

        with self.assertRaises(ValueError):
            obj.set_level('XXX')
