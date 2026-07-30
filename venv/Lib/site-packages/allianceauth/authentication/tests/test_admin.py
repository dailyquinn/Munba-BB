from bs4 import BeautifulSoup
from urllib.parse import quote
from unittest.mock import patch, MagicMock

from django_webtest import WebTest

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory, Client

from allianceauth.authentication.models import (
    CharacterOwnership, State, OwnershipRecord
)
from allianceauth.eveonline.models import (
    EveCharacter, EveCorporationInfo, EveAllianceInfo, EveFactionInfo
)
from allianceauth.services.hooks import ServicesHook
from allianceauth.tests.auth_utils import AuthUtils

from ..admin import (
    BaseUserAdmin,
    CharacterOwnershipAdmin,
    StateAdmin,
    MainCorporationsFilter,
    MainAllianceFilter,
    MainFactionFilter,
    OwnershipRecordAdmin,
    User,
    UserAdmin,
    user_main_organization,
    user_profile_pic,
    user_username,
    update_main_character_model,
    make_service_hooks_update_groups_action,
    make_service_hooks_sync_nickname_action
)
from . import get_admin_change_view_url, get_admin_search_url


MODULE_PATH = 'allianceauth.authentication.admin'


class MockRequest:
    def __init__(self, user=None):
        self.user = user


class TestCaseWithTestData(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        for MyModel in [
            EveAllianceInfo, EveCorporationInfo, EveCharacter, Group, User
        ]:
            MyModel.objects.all().delete()

        # groups
        cls.group_1 = Group.objects.create(
            name='Group 1'
        )
        cls.group_2 = Group.objects.create(
            name='Group 2'
        )

        # user 1 - corp and alliance, normal user
        character_1 = EveCharacter.objects.create(
            character_id=1001,
            character_name='Bruce Wayne',
            corporation_id=2001,
            corporation_name='Wayne Technologies',
            corporation_ticker='WT',
            alliance_id=3001,
            alliance_name='Wayne Enterprises',
            alliance_ticker='WE',
        )
        character_1a = EveCharacter.objects.create(
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
            character_1.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=character_1,
            owner_hash='x1' + character_1.character_name,
            user=cls.user_1
        )
        CharacterOwnership.objects.create(
            character=character_1a,
            owner_hash='x1' + character_1a.character_name,
            user=cls.user_1
        )
        cls.user_1.profile.main_character = character_1
        cls.user_1.profile.save()
        cls.user_1.groups.add(cls.group_1)

        # user 2 - corp only, staff
        character_2 = EveCharacter.objects.create(
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
            character_2.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=character_2,
            owner_hash='x1' + character_2.character_name,
            user=cls.user_2
        )
        cls.user_2.profile.main_character = character_2
        cls.user_2.profile.save()
        cls.user_2.groups.add(cls.group_2)
        cls.user_2.is_staff = True
        cls.user_2.save()

        # user 3 - no main, no group, superuser
        character_3 = EveCharacter.objects.create(
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
            character_3.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=character_3,
            owner_hash='x1' + character_3.character_name,
            user=cls.user_3
        )
        cls.user_3.is_superuser = True
        cls.user_3.save()

        # user 4 - corp and faction, no alliance
        cls.character_4 = EveCharacter.objects.create(
            character_id=4321,
            character_name='Professor X',
            corporation_id=5432,
            corporation_name="Xavier's School for Gifted Youngsters",
            corporation_ticker='MUTNT',
            alliance_id=None,
            faction_id=999,
            faction_name='The X-Men',
        )
        cls.user_4 = User.objects.create_user(
            cls.character_4.character_name.replace(' ', '_'),
            'abc@example.com',
            'password'
        )
        CharacterOwnership.objects.create(
            character=cls.character_4,
            owner_hash='x1' + cls.character_4.character_name,
            user=cls.user_4
        )
        cls.user_4.profile.main_character = cls.character_4
        cls.user_4.profile.save()
        EveFactionInfo.objects.create(faction_id=999, faction_name='The X-Men')


def make_generic_search_request(ModelClass: type, search_term: str):
    User.objects.create_superuser(
        username='superuser', password='secret', email='admin@example.com'
    )
    c = Client()
    c.login(username='superuser', password='secret')
    return c.get(
        f'{get_admin_search_url(ModelClass)}?q={quote(search_term)}'
    )


class TestCharacterOwnershipAdmin(TestCaseWithTestData):
    fixtures = ["disable_analytics"]

    def setUp(self):
        self.modeladmin = CharacterOwnershipAdmin(
            model=User, admin_site=AdminSite()
        )

    def test_change_view_loads_normally(self):
        User.objects.create_superuser(
            username='superuser', password='secret', email='admin@example.com'
        )
        c = Client()
        c.login(username='superuser', password='secret')
        ownership = self.user_1.character_ownerships.first()
        response = c.get(get_admin_change_view_url(ownership))
        self.assertEqual(response.status_code, 200)

    def test_search_works(self):
        obj = CharacterOwnership.objects\
            .filter(user=self.user_1)\
            .first()
        response = make_generic_search_request(type(obj), obj.user.username)
        expected = 200
        self.assertEqual(response.status_code, expected)


class TestOwnershipRecordAdmin(TestCaseWithTestData):
    fixtures = ["disable_analytics"]

    def setUp(self):
        self.modeladmin = OwnershipRecordAdmin(
            model=User, admin_site=AdminSite()
        )

    def test_change_view_loads_normally(self):
        User.objects.create_superuser(
            username='superuser', password='secret', email='admin@example.com'
        )
        c = Client()
        c.login(username='superuser', password='secret')
        ownership_record = OwnershipRecord.objects\
            .filter(user=self.user_1)\
            .first()
        response = c.get(get_admin_change_view_url(ownership_record))
        self.assertEqual(response.status_code, 200)

    def test_search_works(self):
        obj = OwnershipRecord.objects.first()
        response = make_generic_search_request(type(obj), obj.user.username)
        expected = 200
        self.assertEqual(response.status_code, expected)


class TestStateAdmin(TestCaseWithTestData):
    fixtures = ["disable_analytics"]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.modeladmin = StateAdmin(model=User, admin_site=AdminSite())

    def test_change_view_loads_normally(self):
        User.objects.create_superuser(
            username='superuser', password='secret', email='admin@example.com'
        )
        c = Client()
        c.login(username='superuser', password='secret')

        guest_state = AuthUtils.get_guest_state()
        response = c.get(get_admin_change_view_url(guest_state))
        self.assertEqual(response.status_code, 200)

        member_state = AuthUtils.get_member_state()
        response = c.get(get_admin_change_view_url(member_state))
        self.assertEqual(response.status_code, 200)

    def test_search_works(self):
        obj = State.objects.first()
        response = make_generic_search_request(type(obj), obj.name)
        expected = 200
        self.assertEqual(response.status_code, expected)


class TestUserAdmin(TestCaseWithTestData):
    fixtures = ["disable_analytics"]

    def setUp(self):
        self.factory = RequestFactory()
        self.modeladmin = UserAdmin(
            model=User, admin_site=AdminSite()
        )
        self.character_1 = self.user_1.character_ownerships.first().character

    def test_user_profile_pic_u1(self):
        expected = (
            '<img src="https://images.evetech.net/characters/1001/'
            'portrait?size=32" class="img-circle">'
        )
        self.assertEqual(user_profile_pic(self.user_1), expected)

    def test_user_profile_pic_u3(self):
        self.assertIsNone(user_profile_pic(self.user_3))

    def test_user_username_u1(self):
        expected = (
            '<strong><a href="/admin/authentication/user/{}/change/">'
            'Bruce_Wayne</a></strong><br>Bruce Wayne'.format(self.user_1.pk)
        )
        self.assertEqual(user_username(self.user_1), expected)

    def test_user_username_u3(self):
        expected = (
            '<strong><a href="/admin/authentication/user/{}/change/">'
            'Lex_Luthor</a></strong>'.format(self.user_3.pk)
        )
        self.assertEqual(user_username(self.user_3), expected)

    def test_user_main_organization_u1(self):
        expected = 'Wayne Technologies<br>Wayne Enterprises'
        self.assertEqual(user_main_organization(self.user_1), expected)

    def test_user_main_organization_u2(self):
        expected = 'Daily Planet'
        self.assertEqual(user_main_organization(self.user_2), expected)

    def test_user_main_organization_u3(self):
        expected = ''
        self.assertEqual(user_main_organization(self.user_3), expected)

    def test_user_main_organization_u4(self):
        expected = "Xavier's School for Gifted Youngsters<br>The X-Men"
        self.assertEqual(user_main_organization(self.user_4), expected)

    def test_characters_u1(self):
        expected = 'Batman, Bruce Wayne'
        result = self.modeladmin._characters(self.user_1)
        self.assertEqual(result, expected)

    def test_characters_u2(self):
        expected = 'Clark Kent'
        result = self.modeladmin._characters(self.user_2)
        self.assertEqual(result, expected)

    def test_characters_u3(self):
        expected = 'Lex Luthor'
        result = self.modeladmin._characters(self.user_3)
        self.assertEqual(result, expected)

    def test_groups_u1(self):
        expected = 'Group 1'
        result = self.modeladmin._groups(self.user_1)
        self.assertEqual(result, expected)

    def test_groups_u2(self):
        expected = 'Group 2'
        result = self.modeladmin._groups(self.user_2)
        self.assertEqual(result, expected)

    def test_groups_u3(self):
        result = self.modeladmin._groups(self.user_3)
        self.assertIsNone(result)

    def test_state(self):
        expected = 'Guest'
        result = self.modeladmin._state(self.user_1)
        self.assertEqual(result, expected)

    def test_role_u1(self):
        expected = 'User'
        result = self.modeladmin._role(self.user_1)
        self.assertEqual(result, expected)

    def test_role_u2(self):
        expected = 'Staff'
        result = self.modeladmin._role(self.user_2)
        self.assertEqual(result, expected)

    def test_role_u3(self):
        expected = 'Superuser'
        result = self.modeladmin._role(self.user_3)
        self.assertEqual(result, expected)

    def test_list_2_html_w_tooltips_no_cutoff(self):
        items = ['one', 'two', 'three']
        expected = 'one, two, three'
        result = self.modeladmin._list_2_html_w_tooltips(items, 5)
        self.assertEqual(expected, result)

    def test_list_2_html_w_tooltips_w_cutoff(self):
        items = ['one', 'two', 'three']
        expected = (
            '<span data-tooltip="one, two, three" '
            'class="tooltip">one, two, (...)</span>'
        )
        result = self.modeladmin._list_2_html_w_tooltips(items, 2)
        self.assertEqual(expected, result)

    def test_list_2_html_w_tooltips_empty_list(self):
        items = []
        expected = None
        result = self.modeladmin._list_2_html_w_tooltips(items, 5)
        self.assertEqual(expected, result)

    # actions

    @patch(MODULE_PATH + '.UserAdmin.message_user', auto_spec=True, unsafe=True)
    @patch(MODULE_PATH + '.update_character')
    def test_action_update_main_character_model(
        self, mock_task, mock_message_user
    ):
        users_qs = User.objects.filter(pk__in=[self.user_1.pk, self.user_2.pk])
        update_main_character_model(
            self.modeladmin, MockRequest(self.user_1), users_qs
        )
        self.assertEqual(mock_task.delay.call_count, 2)
        self.assertTrue(mock_message_user.called)

    # filters

    def test_filter_main_corporations(self):

        class UserAdminTest(BaseUserAdmin):
            list_filter = (MainCorporationsFilter,)

        my_modeladmin = UserAdminTest(User, AdminSite())

        # Make sure the lookups are correct
        request = self.factory.get('/')
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        filters = changelist.get_filters(request)
        filterspec = filters[0][0]
        expected = [
            (2002, 'Daily Planet'),
            (2001, 'Wayne Technologies'),
            (5432, "Xavier's School for Gifted Youngsters"),
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

        # Make sure the correct queryset is returned
        request = self.factory.get(
            '/',
            {'main_corporation_id__exact': self.character_1.corporation_id}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [self.user_1]
        self.assertSetEqual(set(queryset), set(expected))

    def test_filter_main_alliances(self):

        class UserAdminTest(BaseUserAdmin):
            list_filter = (MainAllianceFilter,)

        my_modeladmin = UserAdminTest(User, AdminSite())

        # Make sure the lookups are correct
        request = self.factory.get('/')
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        filters = changelist.get_filters(request)
        filterspec = filters[0][0]
        expected = [
            (3001, 'Wayne Enterprises'),
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

        # Make sure the correct queryset is returned
        request = self.factory.get(
            '/',
            {'main_alliance_id__exact': self.character_1.alliance_id}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [self.user_1]
        self.assertSetEqual(set(queryset), set(expected))

    def test_filter_main_factions(self):
        class UserAdminTest(BaseUserAdmin):
            list_filter = (MainFactionFilter,)

        my_modeladmin = UserAdminTest(User, AdminSite())

        # Make sure the lookups are correct
        request = self.factory.get('/')
        request.user = self.user_4
        changelist = my_modeladmin.get_changelist_instance(request)
        filters = changelist.get_filters(request)
        filterspec = filters[0][0]
        expected = [
            (999, 'The X-Men'),
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

        # Make sure the correct queryset is returned
        request = self.factory.get(
            '/',
            {'main_faction_id__exact': self.character_4.faction_id}
        )
        request.user = self.user_4
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [self.user_4]
        self.assertSetEqual(set(queryset), set(expected))

    def test_change_view_loads_normally(self):
        User.objects.create_superuser(
            username='superuser', password='secret', email='admin@example.com'
        )
        c = Client()
        c.login(username='superuser', password='secret')
        response = c.get(get_admin_change_view_url(self.user_1))
        self.assertEqual(response.status_code, 200)

    def test_search_works(self):
        obj = User.objects.first()
        response = make_generic_search_request(type(obj), obj.username)
        expected = 200
        self.assertEqual(response.status_code, expected)


class TestStateAdminChangeFormSuperuserExclusiveEdits(WebTest):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.super_admin = User.objects.create_superuser("super_admin")
        cls.staff_admin = User.objects.create_user("staff_admin")
        cls.staff_admin.is_staff = True
        cls.staff_admin.save()
        cls.staff_admin = AuthUtils.add_permissions_to_user_by_name(
            [
                "authentication.add_state",
                "authentication.change_state",
                "authentication.view_state",
            ],
            cls.staff_admin
        )
        cls.superuser_exclusive_fields = ["permissions",]

    def test_should_show_all_fields_to_superuser_for_add(self):
        # given
        self.app.set_user(self.super_admin)
        page = self.app.get("/admin/authentication/state/add/")
        # when
        form = page.forms["state_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.fields)

    def test_should_not_show_all_fields_to_staff_admins_for_add(self):
        # given
        self.app.set_user(self.staff_admin)
        page = self.app.get("/admin/authentication/state/add/")
        # when
        form = page.forms["state_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertNotIn(field, form.fields)

    def test_should_show_all_fields_to_superuser_for_change(self):
        # given
        self.app.set_user(self.super_admin)
        state = AuthUtils.get_member_state()
        page = self.app.get(f"/admin/authentication/state/{state.pk}/change/")
        # when
        form = page.forms["state_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.fields)

    def test_should_not_show_all_fields_to_staff_admin_for_change(self):
        # given
        self.app.set_user(self.staff_admin)
        state = AuthUtils.get_member_state()
        page = self.app.get(f"/admin/authentication/state/{state.pk}/change/")
        # when
        form = page.forms["state_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertNotIn(field, form.fields)


class TestUserAdminChangeForm(TestCase):
    fixtures = ["disable_analytics"]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.modeladmin = UserAdmin(model=User, admin_site=AdminSite())

    def test_should_show_groups_available_to_user_with_blue_state_only(self):
        # given
        superuser = User.objects.create_superuser("Super")
        user = AuthUtils.create_user("bruce_wayne")
        character = AuthUtils.add_main_character_2(
            user,
            name="Bruce Wayne",
            character_id=1001,
            corp_id=2001,
            corp_name="Wayne Technologies"
        )
        blue_state = State.objects.get(name="Blue")
        blue_state.member_characters.add(character)
        member_state = AuthUtils.get_member_state()
        group_1 = Group.objects.create(name="Group 1")
        group_2 = Group.objects.create(name="Group 2")
        group_2.authgroup.states.add(blue_state)
        group_3 = Group.objects.create(name="Group 3")
        group_3.authgroup.states.add(member_state)
        self.client.force_login(superuser)
        # when
        response = self.client.get(f"/admin/authentication/user/{user.pk}/change/")
        # then
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.rendered_content, features="html.parser")
        groups_select = soup.find("select", {"id": "id_groups"}).find_all('option')
        group_ids = {int(option["value"]) for option in groups_select}
        self.assertSetEqual(group_ids, {group_1.pk, group_2.pk})


class TestUserAdminChangeFormSuperuserExclusiveEdits(WebTest):
    fixtures = ["disable_analytics"]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.super_admin = User.objects.create_superuser("super_admin")
        cls.staff_admin = User.objects.create_user("staff_admin")
        cls.staff_admin.is_staff = True
        cls.staff_admin.save()
        cls.staff_admin = AuthUtils.add_permissions_to_user_by_name(
            [
                "auth.change_user",
                "auth.view_user",
                "authentication.change_user",
                "authentication.change_userprofile",
                "authentication.view_user"
            ],
            cls.staff_admin
        )
        cls.superuser_exclusive_fields = [
            "is_staff", "is_superuser", "user_permissions"
        ]

    def setUp(self) -> None:
        self.user = AuthUtils.create_user("bruce_wayne")

    def test_should_show_all_fields_to_superuser_for_change(self):
        # given
        self.app.set_user(self.super_admin)

        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        # when
        form = page.forms["user_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.fields)

    def test_should_not_show_all_fields_to_staff_admin_for_change(self):
        # given
        self.app.set_user(self.staff_admin)
        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        # when
        form = page.forms["user_form"]
        # then
        for field in self.superuser_exclusive_fields:
            with self.subTest(field=field):
                self.assertNotIn(field, form.fields)

    def test_should_allow_super_admin_to_add_restricted_group_to_user(self):
        # given
        self.app.set_user(self.super_admin)
        group_restricted = Group.objects.create(name="restricted group")
        group_restricted.authgroup.restricted = True
        group_restricted.authgroup.save()
        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        form = page.forms["user_form"]
        # when
        form["groups"].select_multiple(texts=["restricted group"])
        response = form.submit("save")
        # then
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertIn(
            "restricted group", self.user.groups.values_list("name", flat=True)
        )

    def test_should_not_allow_staff_admin_to_add_restricted_group_to_user(self):
        # given
        self.app.set_user(self.staff_admin)
        group_restricted = Group.objects.create(name="restricted group")
        group_restricted.authgroup.restricted = True
        group_restricted.authgroup.save()
        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        form = page.forms["user_form"]
        # when
        form["groups"].select_multiple(texts=["restricted group"])
        response = form.submit("save")
        # then
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You are not allowed to add or remove these restricted groups",
            response.text
        )

    def test_should_not_allow_staff_admin_to_remove_restricted_group_from_user(self):
        # given
        self.app.set_user(self.staff_admin)
        group_restricted = Group.objects.create(name="restricted group")
        group_restricted.authgroup.restricted = True
        group_restricted.authgroup.save()
        self.user.groups.add(group_restricted)
        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        form = page.forms["user_form"]
        # when
        form["groups"].select_multiple(texts=[])
        response = form.submit("save")
        # then
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You are not allowed to add or remove these restricted groups",
            response.text
        )

    def test_should_allow_staff_admin_to_add_normal_group_to_user(self):
        # given
        self.app.set_user(self.super_admin)
        Group.objects.create(name="normal group")
        page = self.app.get(f"/admin/authentication/user/{self.user.pk}/change/")
        form = page.forms["user_form"]
        # when
        form["groups"].select_multiple(texts=["normal group"])
        response = form.submit("save")
        # then
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertIn("normal group", self.user.groups.values_list("name", flat=True))


class TestMakeServicesHooksActions(TestCaseWithTestData):

    class MyServicesHookTypeA(ServicesHook):

        def __init__(self):
            super().__init__()
            self.name = 'My Service A'

        def update_groups(self, user):
            pass

        def sync_nicknames(self, user):
            pass

    class MyServicesHookTypeB(ServicesHook):

        def __init__(self):
            super().__init__()
            self.name = 'My Service B'

        def update_groups(self, user):
            pass

        def update_groups_bulk(self, user):
            pass

        def sync_nicknames(self, user):
            pass

        def sync_nicknames_bulk(self, user):
            pass

    def test_service_has_update_groups_only(self):
        service = self.MyServicesHookTypeA()
        mock_service = MagicMock(spec=service)
        action = make_service_hooks_update_groups_action(mock_service)
        action(MagicMock(), MagicMock(), [self.user_1])
        self.assertTrue(mock_service.update_groups.called)

    def test_service_has_update_groups_bulk(self):
        service = self.MyServicesHookTypeB()
        mock_service = MagicMock(spec=service)
        action = make_service_hooks_update_groups_action(mock_service)
        action(MagicMock(), MagicMock(), [self.user_1])
        self.assertFalse(mock_service.update_groups.called)
        self.assertTrue(mock_service.update_groups_bulk.called)

    def test_service_has_sync_nickname_only(self):
        service = self.MyServicesHookTypeA()
        mock_service = MagicMock(spec=service)
        action = make_service_hooks_sync_nickname_action(mock_service)
        action(MagicMock(), MagicMock(), [self.user_1])
        self.assertTrue(mock_service.sync_nickname.called)

    def test_service_has_sync_nicknames_bulk(self):
        service = self.MyServicesHookTypeB()
        mock_service = MagicMock(spec=service)
        action = make_service_hooks_sync_nickname_action(mock_service)
        action(MagicMock(), MagicMock(), [self.user_1])
        self.assertFalse(mock_service.sync_nickname.called)
        self.assertTrue(mock_service.sync_nicknames_bulk.called)
