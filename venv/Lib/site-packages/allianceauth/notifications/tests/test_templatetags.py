from unittest.mock import patch, Mock

from django.test import TestCase, override_settings

from allianceauth.tests.auth_utils import AuthUtils
from ..templatetags.auth_notifications import (
    user_unread_notification_count, notifications_refresh_time
)

MODULE_PATH = 'allianceauth.notifications.templatetags.auth_notifications'

NOTIFICATIONS_REFRESH_TIME_DEFAULT = 66
MY_NOTIFICATIONS_REFRESH_TIME = 23


@patch(MODULE_PATH + '.Notification.objects.user_unread_count')
class TestUserNotificationCount(TestCase):

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

    def test_return_normal(self, mock_user_unread_count):
        unread_count = 42
        mock_user_unread_count.return_value = unread_count

        result = user_unread_notification_count(self.user)
        expected = unread_count
        self.assertEqual(result, expected)
        args, kwargs = mock_user_unread_count.call_args
        self.assertEqual(args[0], self.user.pk)

    def test_return_error_if_non_user(self, mock_user_unread_count):
        unread_count = -1
        mock_user_unread_count.return_value = unread_count

        result = user_unread_notification_count('invalid')
        expected = unread_count
        self.assertEqual(result, expected)


@patch(
    MODULE_PATH + '.Notification.NOTIFICATIONS_REFRESH_TIME_DEFAULT',
    NOTIFICATIONS_REFRESH_TIME_DEFAULT
)
class TestNotificationsRefreshTime(TestCase):

    @override_settings(NOTIFICATIONS_REFRESH_TIME=MY_NOTIFICATIONS_REFRESH_TIME)
    def test_return_from_setting(self):
        result = notifications_refresh_time()
        expected = MY_NOTIFICATIONS_REFRESH_TIME
        self.assertEqual(result, expected)

    @override_settings(NOTIFICATIONS_REFRESH_TIME=0)
    def test_refresh_time_can_be_zero(self):
        result = notifications_refresh_time()
        expected = 0
        self.assertEqual(result, expected)

    @override_settings(NOTIFICATIONS_REFRESH_TIME=None)
    def test_return_default_refresh_time_if_not_exists(self):
        result = notifications_refresh_time()
        expected = NOTIFICATIONS_REFRESH_TIME_DEFAULT
        self.assertEqual(result, expected)

    @override_settings(NOTIFICATIONS_REFRESH_TIME='33')
    def test_return_default_refresh_time_if_not_int(self):
        result = notifications_refresh_time()
        expected = NOTIFICATIONS_REFRESH_TIME_DEFAULT
        self.assertEqual(result, expected)

    @override_settings(NOTIFICATIONS_REFRESH_TIME=-1)
    def test_return_default_refresh_time_if_lt_0(self):
        result = notifications_refresh_time()
        expected = NOTIFICATIONS_REFRESH_TIME_DEFAULT
        self.assertEqual(result, expected)
