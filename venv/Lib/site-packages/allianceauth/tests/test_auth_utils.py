from unittest import mock

from django.contrib.auth.models import User, Group, Permission
from django.test import TestCase

from allianceauth.eveonline.models import (
    EveCorporationInfo, EveAllianceInfo, EveCharacter
)

from .auth_utils import AuthUtils


class TestAuthUtils(TestCase):

    def test_can_create_user(self):
        user = AuthUtils.create_user('Bruce Wayne')
        self.assertTrue(User.objects.filter(username='Bruce Wayne').exists())

    def test_can_add_main_character_2(self):
        user = AuthUtils.create_user('Bruce Wayne')
        character = AuthUtils.add_main_character_2(
            user,
            name='Bruce Wayne',
            character_id=1001,
            corp_id=2001,
            corp_name='Wayne Technologies',
            corp_ticker='WYT',
            alliance_id=3001,
            alliance_name='Wayne Enterprises'
        )
        expected = character
        self.assertEqual(user.profile.main_character, expected)

    def test_can_add_permission_to_group(self):
        group = Group.objects.create(name='Dummy Group')
        p = AuthUtils.get_permission_by_name('auth.group_management')
        AuthUtils.add_permissions_to_groups([p], [group])
        self.assertTrue(group.permissions.filter(pk=p.pk).exists())

    def test_can_add_permission_to_user_by_name(self):
        user = AuthUtils.create_user('Bruce Wayne')
        user = AuthUtils.add_permission_to_user_by_name(
            'auth.timer_management', user
        )
        self.assertTrue(user.has_perm('auth.timer_management'))


class TestGetPermissionByName(TestCase):

    def test_can_get_permission_by_name(self):
        expected = Permission.objects.get(
            content_type__app_label='auth', codename='timer_management'
        )
        self.assertEqual(
            AuthUtils.get_permission_by_name('auth.timer_management'), expected
        )

    def test_raises_exception_on_invalid_permission_format(self):
        with self.assertRaises(ValueError):
            AuthUtils.get_permission_by_name('timer_management')
