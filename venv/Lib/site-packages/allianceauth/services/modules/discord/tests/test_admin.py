from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils.timezone import now

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
)
from allianceauth.utils.testing import NoSocketsTestCase

from ....admin import (
    MainAllianceFilter,
    MainCorporationsFilter,
    ServicesUserAdmin,
    user_main_organization,
    user_profile_pic,
    user_username,
)
from ..admin import DiscordUserAdmin
from ..models import DiscordUser
from . import MODULE_PATH


class TestDataMixin(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        EveCharacter.objects.all().delete()
        EveCorporationInfo.objects.all().delete()
        EveAllianceInfo.objects.all().delete()
        User.objects.all().delete()
        DiscordUser.objects.all().delete()

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
        DiscordUser.objects.create(
            user=cls.user_1,
            uid=1001,
            username='Bruce Wayne',
            discriminator='1234',
            activated=now()
        )

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
        DiscordUser.objects.create(
            user=cls.user_2,
            uid=1002
        )

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
        DiscordUser.objects.create(
            user=cls.user_3,
            uid=1003
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.modeladmin = DiscordUserAdmin(
            model=DiscordUser, admin_site=AdminSite()
        )


class TestColumnRendering(TestDataMixin, NoSocketsTestCase):

    def test_user_profile_pic_u1(self):
        expected = (
            '<img src="https://images.evetech.net/characters/1001/'
            'portrait?size=32" class="img-circle">'
        )
        self.assertEqual(user_profile_pic(self.user_1.discord), expected)

    def test_user_profile_pic_u3(self):
        self.assertIsNone(user_profile_pic(self.user_3.discord))

    def test_user_username_u1(self):
        expected = (
            '<strong><a href="/admin/discord/discorduser/{}/change/">'
            'Bruce_Wayne</a></strong><br>Bruce Wayne'.format(
                self.user_1.discord.pk
            )
        )
        self.assertEqual(user_username(self.user_1.discord), expected)

    def test_user_username_u3(self):
        expected = (
            '<strong><a href="/admin/discord/discorduser/{}/change/">'
            'Lex_Luthor</a></strong>'.format(self.user_3.discord.pk)
        )
        self.assertEqual(user_username(self.user_3.discord), expected)

    def test_user_main_organization_u1(self):
        expected = 'Wayne Technologies<br>Wayne Enterprises'
        result = user_main_organization(self.user_1.discord)
        self.assertEqual(result, expected)

    def test_user_main_organization_u2(self):
        expected = 'Daily Planet'
        result = user_main_organization(self.user_2.discord)
        self.assertEqual(result, expected)

    def test_user_main_organization_u3(self):
        expected = ''
        result = user_main_organization(self.user_3.discord)
        self.assertEqual(result, expected)

    def test_uid(self):
        expected = 1001
        result = self.modeladmin._uid(self.user_1.discord)
        self.assertEqual(result, expected)

    def test_username_when_defined(self):
        expected = 'Bruce Wayne#1234'
        result = self.modeladmin._username(self.user_1.discord)
        self.assertEqual(result, expected)

    def test_username_when_not_defined(self):
        expected = ''
        result = self.modeladmin._username(self.user_2.discord)
        self.assertEqual(result, expected)

    # actions


class TestFilters(TestDataMixin, NoSocketsTestCase):

    def test_filter_main_corporations(self):

        class DiscordUserAdminTest(ServicesUserAdmin):
            list_filter = (MainCorporationsFilter,)

        my_modeladmin = DiscordUserAdminTest(DiscordUser, AdminSite())

        # Make sure the lookups are correct
        request = self.factory.get('/')
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        filters = changelist.get_filters(request)
        filterspec = filters[0][0]
        expected = [
            (2002, 'Daily Planet'),
            (2001, 'Wayne Technologies'),
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

        # Make sure the correct queryset is returned
        request = self.factory.get(
            '/', {'main_corporation_id__exact': self.character_1.corporation_id}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [self.user_1.discord]
        self.assertSetEqual(set(queryset), set(expected))

    def test_filter_main_alliances(self):

        class DiscordUserAdminTest(ServicesUserAdmin):
            list_filter = (MainAllianceFilter,)

        my_modeladmin = DiscordUserAdminTest(DiscordUser, AdminSite())

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
            '/', {'main_alliance_id__exact': self.character_1.alliance_id}
        )
        request.user = self.user_1
        changelist = my_modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        expected = [self.user_1.discord]
        self.assertSetEqual(set(queryset), set(expected))


@patch(MODULE_PATH + ".admin.DiscordUser.delete_user")
class TestDeleteQueryset(TestDataMixin, NoSocketsTestCase):
    def test_should_delete_all_objects(self, mock_delete_user):
        # given
        request = self.factory.get('/')
        request.user = self.user_1
        queryset = DiscordUser.objects.filter(user__in=[self.user_2, self.user_3])
        # when
        self.modeladmin.delete_queryset(request, queryset)
        # then
        self.assertEqual(mock_delete_user.call_count, 2)
