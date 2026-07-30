from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from allianceauth.tests.auth_utils import AuthUtils
from ..models import Notification


MODULE_PATH = 'allianceauth.notifications.models'

NOTIFICATIONS_MAX_PER_USER_DEFAULT = 42


class TestQuerySet(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user_1 = AuthUtils.create_user('Peter Parker')
        cls.user_2 = AuthUtils.create_user('Clark Kent')

    @patch(MODULE_PATH + '.Notification.objects.invalidate_user_notification_cache')
    def test_update_will_invalidate_cache(
        self, mock_invalidate_user_notification_cache
    ):
        Notification.objects.notify_user(self.user_1, 'dummy_1')
        Notification.objects.notify_user(self.user_2, 'dummy_2')
        Notification.objects.update(viewed=True)
        self.assertEqual(mock_invalidate_user_notification_cache.call_count, 2)


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

    def test_can_notify(self):
        title = 'dummy_title'
        message = 'dummy message'
        level = 'danger'
        Notification.objects.notify_user(self.user, title, message, level)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, title)
        self.assertEqual(obj.message, message)
        self.assertEqual(obj.level, level)

    def test_use_message_as_title_if_missing(self):
        title = 'dummy_title'
        Notification.objects.notify_user(self.user, title)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, title)
        self.assertEqual(obj.message, title)

    def test_should_use_default_level_when_not_specified(self):
        # given
        title = 'dummy_title'
        message = 'dummy message'
        # when
        Notification.objects.notify_user(self.user, title, message)
        # then
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, title)
        self.assertEqual(obj.message, message)
        self.assertEqual(obj.level, Notification.Level.INFO)

    def test_should_use_default_level_when_invalid_level_given(self):
        # given
        title = 'dummy_title'
        message = 'dummy message'
        level = "invalid"
        # when
        Notification.objects.notify_user(self.user, title, message, level)
        # then
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, title)
        self.assertEqual(obj.message, message)
        self.assertEqual(obj.level, Notification.Level.INFO)

    @override_settings(NOTIFICATIONS_MAX_PER_USER=3)
    def test_remove_when_too_many_notifications(self):
        Notification.objects.notify_user(self.user, 'dummy')
        obj_2 = Notification.objects.notify_user(self.user, 'dummy')
        obj_3 = Notification.objects.notify_user(self.user, 'dummy')
        obj_4 = Notification.objects.notify_user(self.user, 'dummy')
        expected = {obj_2.pk, obj_3.pk, obj_4.pk}
        result = set(
            Notification.objects.filter(user=self.user).values_list("pk", flat=True)
        )
        self.assertSetEqual(result, expected)
        obj_5 = Notification.objects.notify_user(self.user, 'dummy')
        expected = {obj_3.pk, obj_4.pk, obj_5.pk}
        result = set(
            Notification.objects.filter(user=self.user).values_list("pk", flat=True)
        )
        self.assertSetEqual(result, expected)


@patch("allianceauth.notifications.managers.logger")
@patch(
    MODULE_PATH + ".Notification.NOTIFICATIONS_MAX_PER_USER_DEFAULT",
    NOTIFICATIONS_MAX_PER_USER_DEFAULT
)
class TestMaxNotificationsPerUser(TestCase):
    @override_settings(NOTIFICATIONS_MAX_PER_USER=42)
    def test_should_use_custom_integer_setting(self, mock_logger):
        # when
        result = Notification.objects._max_notifications_per_user()
        # then
        self.assertEqual(result, 42)
        self.assertFalse(mock_logger.warning.called)

    @override_settings(NOTIFICATIONS_MAX_PER_USER="42")
    def test_should_use_custom_string_setting(self, mock_logger):
        # when
        result = Notification.objects._max_notifications_per_user()
        # then
        self.assertEqual(result, 42)
        self.assertFalse(mock_logger.warning.called)

    @override_settings()
    def test_should_use_default_if_not_defined(self, mock_logger):
        # given
        del settings.NOTIFICATIONS_MAX_PER_USER
        # when
        result = Notification.objects._max_notifications_per_user()
        # then
        self.assertEqual(result, NOTIFICATIONS_MAX_PER_USER_DEFAULT)
        self.assertFalse(mock_logger.warning.called)

    @override_settings(NOTIFICATIONS_MAX_PER_USER="abc")
    def test_should_reset_to_default_if_not_int(self, mock_logger):
        # when
        result = Notification.objects._max_notifications_per_user()
        # then
        self.assertEqual(result, NOTIFICATIONS_MAX_PER_USER_DEFAULT)
        self.assertTrue(mock_logger.warning.called)

    @override_settings(NOTIFICATIONS_MAX_PER_USER=-1)
    def test_should_reset_to_default_if_lt_zero(self, mock_logger):
        # when
        result = Notification.objects._max_notifications_per_user()
        # then
        self.assertEqual(result, NOTIFICATIONS_MAX_PER_USER_DEFAULT)
        self.assertTrue(mock_logger.warning.called)


@patch('allianceauth.notifications.managers.cache')
class TestUnreadCount(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user_1 = AuthUtils.create_user('magic_mike')
        AuthUtils.add_main_character(
            cls.user_1,
            'Magic Mike',
            '1',
            corp_id='2',
            corp_name='Pole Riders',
            corp_ticker='PRIDE',
            alliance_id='3',
            alliance_name='RIDERS'
        )

        # test notifications for mike
        Notification.objects.all().delete()
        Notification.objects.create(
            user=cls.user_1,
            level="INFO",
            title="Job 1 Failed",
            message="Because it was broken",
            viewed=True
        )
        Notification.objects.create(
            user=cls.user_1,
            level="INFO",
            title="Job 2 Failed",
            message="Because it was broken"
        )
        Notification.objects.create(
            user=cls.user_1,
            level="INFO",
            title="Job 3 Failed",
            message="Because it was broken"
        )

        cls.user_2 = AuthUtils.create_user('teh_kid')
        AuthUtils.add_main_character(
            cls.user_2,
            'The Kid', '2',
            corp_id='2',
            corp_name='Pole Riders',
            corp_ticker='PRIDE',
            alliance_id='3',
            alliance_name='RIDERS'
        )

        # Notifications for kid
        Notification.objects.create(
            user=cls.user_2,
            level="INFO",
            title="Job 6 Failed",
            message="Because it was broken"
        )

    def test_update_cache_when_not_in_cache(self, mock_cache):
        mock_cache.get.return_value = None

        result = Notification.objects.user_unread_count(self.user_1.pk)
        expected = 2
        self.assertEqual(result, expected)
        self.assertTrue(mock_cache.set.called)
        args, kwargs = mock_cache.set.call_args
        self.assertEqual(
            kwargs['key'],
            Notification.objects._user_notification_cache_key(self.user_1.pk)
        )
        self.assertEqual(kwargs['value'], expected)

    def test_return_from_cache_when_in_cache(self, mock_cache):
        mock_cache.get.return_value = 42
        result = Notification.objects.user_unread_count(self.user_1.pk)
        expected = 42
        self.assertEqual(result, expected)
        self.assertFalse(mock_cache.set.called)

    def test_return_error_code_when_user_not_found(self, mock_cache):
        mock_cache.get.return_value = None
        invalid_user_id = max(user.pk for user in User.objects.all()) + 1
        result = Notification.objects.user_unread_count(invalid_user_id)
        expected = -1
        self.assertEqual(result, expected)
        self.assertFalse(mock_cache.set.called)

    def test_can_invalidate_cache(self, mock_cache):
        Notification.objects.invalidate_user_notification_cache(self.user_1.pk)
        self.assertTrue(mock_cache.delete)
        args, kwargs = mock_cache.delete.call_args
        self.assertEqual(
            kwargs['key'],
            Notification.objects._user_notification_cache_key(self.user_1.pk)
        )
