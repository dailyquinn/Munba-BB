from django.test import TestCase
from allianceauth.tests.auth_utils import AuthUtils

from .. import notify
from ..models import Notification


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

    def test_can_notify_short(self):
        # when
        notify(self.user, "dummy")
        # then
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_can_notify_full(self):
        # when
        notify(user=self.user, title="title", message="message", level="danger")
        # then
        obj = Notification.objects.first()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.title, "title")
        self.assertEqual(obj.message, "message")
        self.assertEqual(obj.level, "danger")
