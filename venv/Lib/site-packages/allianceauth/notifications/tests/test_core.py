from django.test import TestCase

from allianceauth.tests.auth_utils import AuthUtils

from ..core import NotifyApiWrapper
from ..models import Notification


class TestUserNotificationCount(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = AuthUtils.create_user("bruce_wayne")

    def test_should_add_danger_notification(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify.danger(user=self.user, title="title", message="message")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.DANGER)

    def test_should_add_info_notification(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify.info(user=self.user, title="title", message="message")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.INFO)

    def test_should_add_success_notification(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify.success(user=self.user, title="title", message="message")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.SUCCESS)

    def test_should_add_warning_notification(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify.warning(user=self.user, title="title", message="message")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.WARNING)

    def test_should_add_info_notification_via_callable(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify(user=self.user, title="title", message="message")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.INFO)

    def test_should_add_danger_notification_via_callable(self):
        # given
        notify = NotifyApiWrapper()
        # when
        notify(user=self.user, title="title", message="message", level="danger")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, Notification.Level.DANGER)
