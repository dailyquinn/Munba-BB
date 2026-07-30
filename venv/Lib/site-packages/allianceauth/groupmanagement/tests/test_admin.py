from unittest.mock import patch

from django_webtest import WebTest

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase, override_settings

from allianceauth.authentication.models import CharacterOwnership, State
from allianceauth.eveonline.models import (
    EveAllianceInfo, EveCharacter, EveCorporationInfo,
)
from allianceauth.tests.auth_utils import AuthUtils

from ..admin import Group, GroupAdmin, HasLeaderFilter
from ..models import ReservedGroupName
from . import get_admin_change_view_url

if 'allianceauth.eveonline.autogroups' in settings.INSTALLED_APPS:
    _has_auto_groups = True
    from allianceauth.eveonline.autogroups.models import AutogroupsConfig

    from ..admin import IsAutoGroupFilter
else:
    _has_auto_groups = False


MODULE_PATH = 'allianceauth.groupmanagement.admin'


class MockRequest:

    def __init__(self, user=None):
        self.user = user


class TestGroupAdmin(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # group 1 - has leader
        cls.group_1 = Group.objects.create(name='Group 1')
        cls.group_1.authgroup.description = 'Default Group'
        cls.group_1.authgroup.internal = False
        cls.group_1.authgroup.hidden = False
        cls.group_1.authgroup.save()

        # group 2 - no leader
        cls.group_2 = Group.objects.create(name='Group 2')
        cls.group_2.authgroup.description = 'Internal Group'
        cls.group_2.authgroup.internal = True
        cls.group_2.authgroup.group_leader_groups.add(cls.group_1)
        cls.group_2.authgroup.save()

        # group 3 - has leader
        cls.group_3 = Group.objects.create(name='Group 3')
        cls.group_3.authgroup.description = 'Hidden Group'
        cls.group_3.authgroup.internal = False
        cls.group_3.authgroup.hidden = True
        cls.group_3.authgroup.save()

        # group 4 - no leader
        cls.group_4 = Group.objects.create(name='Group 4')
        cls.group_4.authgroup.description = 'Open Group'
        cls.group_4.authgroup.internal = False
        cls.group_4.authgroup.hidden = False
        cls.group_4.authgroup.open = True
        cls.group_4.authgroup.save()

        # group 5 - no leader
        cls.group_5 = Group.objects.create(name='Group 5')
        cls.group_5.authgroup.description = 'Public Group'
        cls.group_5.authgroup.internal = False
        cls.group_5.authgroup.hidden = False
        cls.group_5.authgroup.public = True
        cls.group_5.authgroup.save()

        # group 6 - no leader
        cls.group_6 = Group.objects.create(name='Group 6')
        cls.group_6.authgroup.description = 'Mixed Group'
        cls.group_6.authgroup.internal = False
        cls.group_6.authgroup.hidden = True
        cls.group_6.authgroup.open = True
        cls.group_6.authgroup.public = True
        cls.group_6.authgroup.save()

        # user 1 - corp and alliance, normal user
        cls.character_1 = EveCharacter.objects.create(
            character_id=1001,
            character_name='Bruce Wayne',
            corporation_id=2001,
            corporation_name='Wayne Technologies',
            corporation_ticker='WT',
            alliance_id=3001,
            alliance_name='Wayne Enterprises',
            alliance_ticker='WE',
        )
        cls.character_1a = EveCharacter.objects.create(
            character_id=1002,
            character_name='Batman',
            corporation_id=2001,
            corporation_name='Wayne Technologies',
            corporation_ticker='WT',
            alliance_id=3001,
            alliance_name='Wayne Enterprises',
            alliance_ticker='WE',
        )
        alliance = EveAllianceInfo.objects.create(
            alliance_id=3001,
            alliance_name='Wayne Enterprises',
            alliance_ticker='WE',
            executor_corp_id=2001
        )
        EveCorporationInfo.objects.create(
            corporation_id=2001,
            corporation_name='Wayne Technologies',
            corporation_ticker='WT',
            member_count=42,
            alliance=alliance
        )
        cls.user_1 = User.objects.create_user(
            cls.character_1.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=cls.character_1,
            owner_hash='x1' + cls.character_1.character_name,
            user=cls.user_1
        )
        CharacterOwnership.objects.create(
            character=cls.character_1a,
            owner_hash='x1' + cls.character_1a.character_name,
            user=cls.user_1
        )
        cls.user_1.profile.main_character = cls.character_1
        cls.user_1.profile.save()
        cls.user_1.groups.add(cls.group_1)
        cls.group_1.authgroup.group_leaders.add(cls.user_1)

        # user 2 - corp only, staff
        cls.character_2 = EveCharacter.objects.create(
            character_id=1003,
            character_name='Clark Kent',
            corporation_id=2002,
            corporation_name='Daily Planet',
            corporation_ticker='DP',
            alliance_id=None
        )
        EveCorporationInfo.objects.create(
            corporation_id=2002,
            corporation_name='Daily Plane',
            corporation_ticker='DP',
            member_count=99,
            alliance=None
        )
        cls.user_2 = User.objects.create_user(
            cls.character_2.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=cls.character_2,
            owner_hash='x1' + cls.character_2.character_name,
            user=cls.user_2
        )
        cls.user_2.profile.main_character = cls.character_2
        cls.user_2.profile.save()
        cls.user_2.groups.add(cls.group_2)
        cls.user_2.is_staff = True
        cls.user_2.save()

        # user 3 - no main, no group, superuser
        cls.character_3 = EveCharacter.objects.create(
            character_id=1101,
            character_name='Lex Luthor',
            corporation_id=2101,
            corporation_name='Lex Corp',
            corporation_ticker='LC',
            alliance_id=None
        )
        EveCorporationInfo.objects.create(
            corporation_id=2101,
            corporation_name='Lex Corp',
            corporation_ticker='LC',
            member_count=666,
            alliance=None
        )
        EveAllianceInfo.objects.create(
            alliance_id=3101,
            alliance_name='Lex World Domination',
            alliance_ticker='LWD',
            executor_corp_id=2101
        )
        cls.user_3 = User.objects.create_user(
            cls.character_3.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=cls.character_3,
            owner_hash='x1' + cls.character_3.character_name,
            user=cls.user_3
        )
        cls.user_3.is_superuser = True
        cls.user_3.save()
        cls.user_3.groups.add(cls.group_3)
        cls.group_3.authgroup.group_leaders.add(cls.user_3)

    def setUp(self):
        self.factory = RequestFactory()
        self.modeladmin = GroupAdmin(
            model=Group, admin_site=AdminSite()
        )

    def _create_autogroups(self):
        """create autogroups for corps and alliances"""
        if _has_auto_groups:
            autogroups_config = AutogroupsConfig(
                corp_groups=True,
                alliance_groups=True
            )
            autogroups_config.save()
            for state in State.objects.all():
                autogroups_config.states.add(state)
            autogroups_config.update_corp_group_membership(self.user_1)

    # column rendering

    def test_description(self):
        expected = 'Default Group'
        result = self.modeladmin._description(self.group_1)
        self.assertEqual(result, expected)

    def test_member_count(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_1.pk)
        # when
        result = self.modeladmin._member_count(obj)
        # then
        self.assertEqual(result, 1)

    def test_has_leader_user(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_1.pk)
        # when
        result = self.modeladmin.has_leader(obj)
        # then
        self.assertTrue(result)

    def test_has_leader_group(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_2.pk)
        # when
        result = self.modeladmin.has_leader(obj)
        # then
        self.assertTrue(result)

    def test_properties_1(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_1.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Default'])

    def test_properties_2(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_2.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Internal'])

    def test_properties_3(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_3.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Hidden'])

    def test_properties_4(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_4.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Open'])

    def test_properties_5(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_5.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Public'])

    def test_properties_6(self):
        # given
        request = MockRequest(user=self.user_1)
        obj = self.modeladmin.get_queryset(request).get(pk=self.group_6.pk)
        # when
        result = self.modeladmin._properties(obj)
        self.assertListEqual(result, ['Hidden', 'Open', 'Public'])

    if _has_auto_groups:
        @patch(MODULE_PATH + '._has_auto_groups', True)
        def test_should_show_autogroup_for_corporation(self):
            # given
            self._create_autogroups()
            request = MockRequest(user=self.user_1)
            queryset = self.modeladmin.get_queryset(request)
            obj = queryset.filter(managedcorpgroup__isnull=False).first()
            # when
            result = self.modeladmin._properties(obj)
            # then
            self.assertListEqual(result, ['Auto Group'])

        @patch(MODULE_PATH + '._has_auto_groups', True)
        def test_should_show_autogroup_for_alliance(self):
            # given
            self._create_autogroups()
            request = MockRequest(user=self.user_1)
            queryset = self.modeladmin.get_queryset(request)
            obj = queryset.filter(managedalliancegroup__isnull=False).first()
            # when
            result = self.modeladmin._properties(obj)
            # then
            self.assertListEqual(result, ['Auto Group'])

    # actions

    # filters

    if _has_auto_groups:
        @patch(MODULE_PATH + '._has_auto_groups', True)
        def test_filter_is_auto_group(self):

            class GroupAdminTest(admin.ModelAdmin):
                list_filter = (IsAutoGroupFilter,)

            self._create_autogroups()
            my_modeladmin = GroupAdminTest(Group, AdminSite())

            # Make sure the lookups are correct
            request = self.factory.get('/')
            request.user = self.user_1
            changelist = my_modeladmin.get_changelist_instance(request)
            filters = changelist.get_filters(request)
            filterspec = filters[0][0]
            expected = [
                ('yes', 'Yes'),
                ('no', 'No'),
            ]
            self.assertEqual(filterspec.lookup_choices, expected)

            # Make sure the correct queryset is returned - no
            request = self.factory.get(
                '/', {'is_auto_group__exact': 'no'}
            )
            request.user = self.user_1
            changelist = my_modeladmin.get_changelist_instance(request)
            queryset = changelist.get_queryset(request)
            expected = [
                self.group_1,
                self.group_2,
                self.group_3,
                self.group_4,
                self.group_5,
                self.group_6
            ]
            self.assertSetEqual(set(queryset), set(expected))

            # Make sure the correct queryset is returned - yes
            request = self.factory.get(
                '/', {'is_auto_group__exact': 'yes'}
            )
            request.user = self.user_1
            changelist = my_modeladmin.get_changelist_instance(request)
            queryset = changelist.get_queryset(request)
            expected = Group.objects.exclude(
                managedalliancegroup__isnull=True,
                managedcorpgroup__isnull=True
            )
            self.assertSetEqual(set(queryset), set(expected))

    def test_filter_has_leader(self):

        class GroupAdminTest(admin.ModelAdmin):
            list_filter = (HasLeaderFilter,)

        self._create_autogroups()
        my_modeladmin = GroupAdminTest(Group, AdminSite())

        # Make sure the lookups are correct
        request = self.factory.get('/')
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        filters = changelist.get_filters(request)
        filterspec = filters[0][0]
        expected = [
            ('yes', 'Yes'),
            ('no', 'No'),
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

        # Make sure the correct queryset is returned - no
        request = self.factory.get(
            '/', {'has_leader__exact': 'no'}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = Group.objects.exclude(pk__in=[
            self.group_1.pk, self.group_3.pk
        ])
        self.assertSetEqual(set(queryset), set(expected))

        # Make sure the correct queryset is returned - yes
        request = self.factory.get(
            '/', {'has_leader__exact': 'yes'}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [
            self.group_1,
            self.group_3
        ]
        self.assertSetEqual(set(queryset), set(expected))

    def test_change_view_loads_normally(self):
        User.objects.create_superuser(
            username='superuser', password='secret', email='admin@example.com'
        )
        c = Client()
        c.login(username='superuser', password='secret')
        response = c.get(get_admin_change_view_url(self.group_1))
        self.assertEqual(response.status_code, 200)

    def test_should_create_new_group(self):
        # given
        user = User.objects.create_superuser("bruce")
        self.client.force_login(user)
        # when
        response = self.client.post(
            "/admin/groupmanagement/group/add/",
            data={
                "name": "new group",
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 0,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
            }
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/group/")
        self.assertTrue(Group.objects.filter(name="new group").exists())

    def test_should_not_allow_creating_new_group_with_reserved_name(self):
        # given
        ReservedGroupName.objects.create(
            name="new group", reason="dummy", created_by="bruce"
        )
        user = User.objects.create_superuser("bruce")
        self.client.force_login(user)
        # when
        response = self.client.post(
            "/admin/groupmanagement/group/add/",
            data={
                "name": "New group",
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 0,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
            }
        )
        # then
        self.assertContains(
            response, "This name has been reserved and can not be used for groups"
        )
        self.assertFalse(Group.objects.filter(name="new group").exists())

    def test_should_not_allow_changing_name_of_existing_group_to_reserved_name(self):
        # given
        ReservedGroupName.objects.create(
            name="new group", reason="dummy", created_by="bruce"
        )
        group = Group.objects.create(name="dummy")
        user = User.objects.create_superuser("bruce")
        self.client.force_login(user)
        # when
        response = self.client.post(
            f"/admin/groupmanagement/group/{group.pk}/change/",
            data={
                "name": "new group",
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 0,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
            }
        )
        # then
        self.assertContains(
            response, "This name has been reserved and can not be used for groups"
        )
        self.assertFalse(Group.objects.filter(name="new group").exists())


class TestGroupAdminChangeFormSuperuserExclusiveEdits(WebTest):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.super_admin = User.objects.create_superuser("super_admin")
        cls.staff_admin = User.objects.create_user("staff_admin")
        cls.staff_admin.is_staff = True
        cls.staff_admin.save()
        cls.staff_admin = AuthUtils.add_permissions_to_user_by_name(
            [
                "auth.add_group",
                "auth.change_group",
                "auth.view_group",
                "groupmanagement.add_group",
                "groupmanagement.change_group",
                "groupmanagement.view_group",
            ],
            cls.staff_admin
        )
        cls.superuser_exclusive_fields = ["permissions", "authgroup-0-restricted"]

    def test_should_show_all_fields_to_superuser_for_add(self):
        # given
        self.app.set_user(self.super_admin)
        page = self.app.get("/admin/groupmanagement/group/add/")
        # when
        form = page.forms["group_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.fields)

    def test_should_not_show_all_fields_to_staff_admins_for_add(self):
        # given
        self.app.set_user(self.staff_admin)
        page = self.app.get("/admin/groupmanagement/group/add/")
        # when
        form = page.forms["group_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertNotIn(field, form.fields)

    def test_should_show_all_fields_to_superuser_for_change(self):
        # given
        self.app.set_user(self.super_admin)
        group = Group.objects.create(name="Dummy group")
        page = self.app.get(f"/admin/groupmanagement/group/{group.pk}/change/")
        # when
        form = page.forms["group_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.fields)

    def test_should_not_show_all_fields_to_staff_admin_for_change(self):
        # given
        self.app.set_user(self.staff_admin)
        group = Group.objects.create(name="Dummy group")
        page = self.app.get(f"/admin/groupmanagement/group/{group.pk}/change/")
        # when
        form = page.forms["group_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertNotIn(field, form.fields)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestGroupAdmin2(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.superuser = User.objects.create_superuser("super")

    def test_should_remove_users_from_state_groups(self):
        # given
        user_member = AuthUtils.create_user("Bruce Wayne")
        character_member = AuthUtils.add_main_character_2(
            user_member,
            name="Bruce Wayne",
            character_id=1001,
            corp_id=2001,
            corp_name="Wayne Technologies",
        )
        user_guest = AuthUtils.create_user("Lex Luthor")
        AuthUtils.add_main_character_2(
            user_guest,
            name="Lex Luthor",
            character_id=1011,
            corp_id=2011,
            corp_name="Luthor Corp",
        )
        member_state = AuthUtils.get_member_state()
        member_state.member_characters.add(character_member)
        user_member.refresh_from_db()
        user_guest.refresh_from_db()
        group = Group.objects.create(name="dummy")
        user_member.groups.add(group)
        user_guest.groups.add(group)
        group.authgroup.states.add(member_state)
        self.client.force_login(self.superuser)
        # when
        response = self.client.post(
            f"/admin/groupmanagement/group/{group.pk}/change/",
            data={
                "name": group.name,
                "users": [user_member.pk, user_guest.pk],
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 1,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
                "authgroup-0-states": member_state.pk,
                "authgroup-0-internal": "on",
                "authgroup-0-hidden": "on",
                "authgroup-0-group": group.pk,
            }
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/group/")
        self.assertIn(group, user_member.groups.all())
        self.assertNotIn(group, user_guest.groups.all())

    def test_should_add_user_to_existing_group(self):
        # given
        user_bruce = AuthUtils.create_user("Bruce Wayne")
        user_lex = AuthUtils.create_user("Lex Luthor")
        group = Group.objects.create(name="dummy")
        user_bruce.groups.add(group)
        self.client.force_login(self.superuser)
        # when
        response = self.client.post(
            f"/admin/groupmanagement/group/{group.pk}/change/",
            data={
                "name": group.name,
                "users": [user_bruce.pk, user_lex.pk],
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 1,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
                "authgroup-0-internal": "on",
                "authgroup-0-hidden": "on",
                "authgroup-0-group": group.pk,
            }
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/group/")
        self.assertIn(group, user_bruce.groups.all())
        self.assertIn(group, user_lex.groups.all())

    def test_should_remove_user_from_existing_group(self):
        # given
        user_bruce = AuthUtils.create_user("Bruce Wayne")
        user_lex = AuthUtils.create_user("Lex Luthor")
        group = Group.objects.create(name="dummy")
        user_bruce.groups.add(group)
        user_lex.groups.add(group)
        self.client.force_login(self.superuser)
        # when
        response = self.client.post(
            f"/admin/groupmanagement/group/{group.pk}/change/",
            data={
                "name": group.name,
                "users": user_bruce.pk,
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 1,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
                "authgroup-0-internal": "on",
                "authgroup-0-hidden": "on",
                "authgroup-0-group": group.pk,
            }
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/group/")
        self.assertIn(group, user_bruce.groups.all())
        self.assertNotIn(group, user_lex.groups.all())

    def test_should_include_user_when_creating_group(self):
        # given
        user_bruce = AuthUtils.create_user("Bruce Wayne")
        self.client.force_login(self.superuser)
        # when
        response = self.client.post(
            "/admin/groupmanagement/group/add/",
            data={
                "name": "new group",
                "users": user_bruce.pk,
                "authgroup-TOTAL_FORMS": 1,
                "authgroup-INITIAL_FORMS": 0,
                "authgroup-MIN_NUM_FORMS": 0,
                "authgroup-MAX_NUM_FORMS": 1,
            }
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/group/")
        group = Group.objects.get(name="new group")
        self.assertIn(group, user_bruce.groups.all())


class TestReservedGroupNameAdmin(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_superuser("bruce")

    def test_should_create_new_entry(self):
        # given
        self.client.force_login(self.user)
        # when
        response = self.client.post(
            "/admin/groupmanagement/reservedgroupname/add/",
            data={"name": "Test", "reason": "dummy"}
        )
        # then
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/groupmanagement/reservedgroupname/")
        obj = ReservedGroupName.objects.get(name="test")
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.created_by, self.user.username)
        self.assertTrue(obj.created_at)

    def test_should_not_allow_names_of_existing_groups(self):
        # given
        Group.objects.create(name="Already taken")
        self.client.force_login(self.user)
        # when
        response = self.client.post(
            "/admin/groupmanagement/reservedgroupname/add/",
            data={"name": "already taken", "reason": "dummy"}
        )
        # then
        self.assertContains(response, "There already exists a group with that name")
        self.assertFalse(ReservedGroupName.objects.filter(name="already taken").exists())
