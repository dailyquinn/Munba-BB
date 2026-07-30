from logging import LogRecord, DEBUG

from django.contrib.auth.models import Permission, Group, User
from django.test import TestCase
from allianceauth.tests.auth_utils import AuthUtils

from ..handlers import NotificationHandler
from ..models import Notification

MODULE_PATH = 'allianceauth.notifications.handlers'


class TestHandler(TestCase):
    def test_do_nothing_if_permission_does_not_exist(self):
        # given
        Permission.objects.get(codename="logging_notifications").delete()
        handler = NotificationHandler()
        record = LogRecord(
            name="name",
            level=DEBUG,
            pathname="pathname",
            lineno=42,
            msg="msg",
            args=[],
            exc_info=None,
            func="func"
        )
        # when
        handler.emit(record)
        # then
        self.assertEqual(Notification.objects.count(), 0)

    def test_should_emit_message_to_users_with_permission_only(self):
        # given
        AuthUtils.create_user('Lex Luthor')
        user_permission = AuthUtils.create_user('Bruce Wayne')
        user_permission = AuthUtils.add_permission_to_user_by_name(
            "auth.logging_notifications", user_permission
        )
        group = Group.objects.create(name="Dummy Group")
        perm = Permission.objects.get(codename="logging_notifications")
        group.permissions.add(perm)
        user_group = AuthUtils.create_user('Peter Parker')
        user_group.groups.add(group)
        user_superuser = User.objects.create_superuser("Clark Kent")
        handler = NotificationHandler()
        record = LogRecord(
            name="name",
            level=DEBUG,
            pathname="pathname",
            lineno=42,
            msg="msg",
            args=[],
            exc_info=None,
            func="func"
        )
        # when
        handler.emit(record)
        # then
        self.assertEqual(Notification.objects.count(), 3)
        users = set(Notification.objects.values_list("user__pk", flat=True))
        self.assertSetEqual(
            users, {user_permission.pk, user_group.pk, user_superuser.pk}
        )
        notif = Notification.objects.first()
        self.assertEqual(notif.user, user_permission)
        self.assertEqual(notif.title, "DEBUG [func:42]")
        self.assertEqual(notif.level, "success")
        self.assertEqual(notif.message, "msg")
