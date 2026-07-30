"""Integration tests

Testing all components of the service, with the exception of the Discord API.

Please note that these tests require Redis and will flush it
"""
import dataclasses
import json
import logging
from unittest.mock import Mock, patch
from uuid import uuid1

import requests_mock
from requests.exceptions import HTTPError

from django.contrib.auth.models import Group, User
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django_webtest import WebTest

from allianceauth.authentication.models import State
from allianceauth.eveonline.models import EveCharacter
from allianceauth.groupmanagement.models import ReservedGroupName
from allianceauth.notifications.models import Notification
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.cache import get_redis_client
from allianceauth.utils.testing import NoSocketsTestCase

from .. import tasks
from ..core import create_bot_client
from ..discord_client import DiscordApiBackoff
from ..discord_client.app_settings import DISCORD_API_BASE_URL
from ..discord_client.tests.factories import (
    TEST_GUILD_ID,
    TEST_USER_ID,
    TEST_USER_NAME,
    create_discord_error_response_unknown_member,
    create_discord_guild_member_object,
    create_discord_guild_object,
    create_discord_role_object,
    create_discord_user_object,
)
from ..models import DiscordUser
from . import MODULE_PATH, TEST_MAIN_ID, TEST_MAIN_NAME, add_permissions_to_members
from .factories import create_discord_user, create_user

logger = logging.getLogger('allianceauth')

ROLE_ALPHA = create_discord_role_object(id=1, name="alpha")
ROLE_BRAVO = create_discord_role_object(id=2, name="bravo")
ROLE_CHARLIE = create_discord_role_object(id=3, name="charlie")
ROLE_CHARLIE_2 = create_discord_role_object(id=4, name="Charlie")  # Discord roles are case sensitive
ROLE_MIKE = create_discord_role_object(id=13, name="mike", managed=True)
ROLE_MEMBER = create_discord_role_object(99, 'Member')
ROLE_BLUE = create_discord_role_object(98, 'Blue')


@dataclasses.dataclass(frozen=True)
class DiscordRequest:
    """Helper for comparing requests made to the Discord API."""
    method: str
    url: str
    text: str = dataclasses.field(compare=False, default=None)

    def json(self):
        return json.loads(self.text)


user_get_current_request = DiscordRequest(
    method='GET',
    url=f'{DISCORD_API_BASE_URL}users/@me'
)
guild_infos_request = DiscordRequest(
    method='GET',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}'
)
guild_roles_request = DiscordRequest(
    method='GET',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/roles'
)
create_guild_role_request = DiscordRequest(
    method='POST',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/roles'
)
guild_member_request = DiscordRequest(
    method='GET',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/{TEST_USER_ID}'
)
add_guild_member_request = DiscordRequest(
    method='PUT',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/{TEST_USER_ID}'
)
modify_guild_member_request = DiscordRequest(
    method='PATCH',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/{TEST_USER_ID}'
)
remove_guild_member_request = DiscordRequest(
    method='DELETE',
    url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/{TEST_USER_ID}'
)


def clear_cache():
    redis = get_redis_client()
    redis.flushall()
    logger.info('Cache flushed')


def reset_testdata():
    AuthUtils.disconnect_signals()
    Group.objects.all().delete()
    User.objects.all().delete()
    State.objects.all().delete()
    EveCharacter.objects.all().delete()
    AuthUtils.connect_signals()
    Notification.objects.all().delete()


@patch(MODULE_PATH + '.core.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.models.DISCORD_GUILD_ID', TEST_GUILD_ID)
@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=False)
@requests_mock.Mocker()
class TestServiceFeatures(TransactionTestCase):
    fixtures = ['disable_analytics.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None

    def setUp(self):
        """All tests: Given a user with member state,
        service permission and active Discord account
        """
        clear_cache()
        reset_testdata()
        self.group_charlie = Group.objects.create(name='charlie')

        # States
        self.member_state = AuthUtils.get_member_state()
        self.guest_state = AuthUtils.get_guest_state()
        self.blue_state = AuthUtils.create_state("Blue", 50)
        permission = AuthUtils.get_permission_by_name('discord.access_discord')
        self.member_state.permissions.add(permission)
        self.blue_state.permissions.add(permission)

        # Test user
        self.user = AuthUtils.create_user(TEST_USER_NAME)
        self.main = AuthUtils.add_main_character_2(
            self.user,
            TEST_MAIN_NAME,
            TEST_MAIN_ID,
            corp_id='2',
            corp_name='test_corp',
            corp_ticker='TEST',
            disconnect_signals=True
        )
        self.member_state.member_characters.add(self.main)

        # verify user is a member and has an account
        self.user = User.objects.get(pk=self.user.pk)
        self.assertEqual(self.user.profile.state, self.member_state)

        self.discord_user = DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))

    @patch(MODULE_PATH + '.auth_hooks.DISCORD_SYNC_NAMES', True)
    def test_when_name_of_main_changes_then_discord_nick_is_updated(
        self, requests_mocker
    ):
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)

        # changing nick to trigger signals
        new_nick = f'Testnick {uuid1().hex}'[:32]
        self.user.profile.main_character.character_name = new_nick
        self.user.profile.main_character.save()

        # verify Discord nick was updates
        nick_updated = False
        for r in requests_mocker.request_history:
            my_request = DiscordRequest(r.method, r.url)
            if my_request == modify_guild_member_request and "nick" in r.json():
                nick_updated = True
                self.assertEqual(r.json()["nick"], new_nick)

        self.assertTrue(nick_updated)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))

    @patch(MODULE_PATH + '.auth_hooks.DISCORD_SYNC_NAMES', True)
    def test_when_name_of_main_changes_and_user_deleted_then_account_is_deleted(
        self, requests_mocker
    ):
        requests_mocker.patch(
            modify_guild_member_request.url, status_code=404, json={'code': 10007}
        )
        requests_mocker.delete(remove_guild_member_request.url, status_code=204)

        # changing nick to trigger signals
        new_nick = f'Testnick {uuid1().hex}'[:32]
        self.user.profile.main_character.character_name = new_nick
        self.user.profile.main_character.save()

        self.assertFalse(DiscordUser.objects.user_has_account(self.user))

    def test_when_name_of_main_changes_and_and_rate_limited_then_dont_call_api(
        self, requests_mocker
    ):
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)

        # exhausting rate limit
        client = create_bot_client()
        client._redis.set(
            name=client._KEY_GLOBAL_RATE_LIMIT_REMAINING,
            value=0,
            px=2000
        )

        # changing nick to trigger signals
        new_nick = f'Testnick {uuid1().hex}'[:32]
        self.user.profile.main_character.character_name = new_nick
        self.user.profile.main_character.save()

        # should not have called the API
        requests_made = [
            DiscordRequest(r.method, r.url) for r in requests_mocker.request_history
        ]
        self.assertListEqual(requests_made, list())

    def test_when_member_is_demoted_to_guest_then_his_account_is_deleted(
        self, requests_mocker
    ):
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)
        requests_mocker.delete(remove_guild_member_request.url, status_code=204)

        # our user is a member and has an account
        self.assertTrue(self.user.has_perm('discord.access_discord'))

        # now we demote him to guest
        self.member_state.member_characters.remove(self.main)

        # verify user is now guest
        self.user = User.objects.get(pk=self.user.pk)
        self.assertEqual(self.user.profile.state, AuthUtils.get_guest_state())

        # verify user has no longer access to Discord and no account
        self.assertFalse(self.user.has_perm('discord.access_discord'))
        self.assertFalse(DiscordUser.objects.user_has_account(self.user))

        # verify account was actually deleted from Discord server
        requests_made = [
            DiscordRequest(r.method, r.url) for r in requests_mocker.request_history
        ]
        self.assertIn(remove_guild_member_request, requests_made)

        # verify user has been notified
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

    def test_when_member_changes_to_blue_state_then_roles_are_updated_accordingly(
        self, requests_mocker
    ):
        # request mocks
        requests_mocker.get(
            guild_member_request.url,
            json=create_discord_guild_member_object(roles=[3, 13, 99])
        )
        requests_mocker.get(
            guild_roles_request.url,
            json=[
                ROLE_ALPHA, ROLE_BRAVO, ROLE_CHARLIE, ROLE_MIKE, ROLE_MEMBER, ROLE_BLUE
            ]
        )
        requests_mocker.post(create_guild_role_request.url, json=ROLE_CHARLIE)
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)

        AuthUtils.disconnect_signals()
        self.user.groups.add(self.group_charlie)
        AuthUtils.connect_signals()

        # demote user to blue state
        self.blue_state.member_characters.add(self.main)
        self.member_state.member_characters.remove(self.main)

        # verify roles for user where updated
        roles_updated = False
        for r in requests_mocker.request_history:
            my_request = DiscordRequest(r.method, r.url)
            if my_request == modify_guild_member_request and "roles" in r.json():
                roles_updated = True
                self.assertSetEqual(set(r.json()["roles"]), {3, 13, 98})
                break

        self.assertTrue(roles_updated)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))

    def test_when_group_added_to_member_and_role_known_then_his_roles_are_updated(
        self, requests_mocker
    ):
        requests_mocker.get(
            guild_member_request.url,
            json=create_discord_guild_member_object(roles=[13, 99])
        )
        requests_mocker.get(
            guild_roles_request.url,
            json=[ROLE_ALPHA, ROLE_BRAVO, ROLE_CHARLIE, ROLE_MIKE, ROLE_MEMBER]
        )
        requests_mocker.post(create_guild_role_request.url, json=ROLE_CHARLIE)
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)

        # adding new group to trigger signals
        self.user.groups.add(self.group_charlie)

        # verify roles for user where updated
        roles_updated = False
        for r in requests_mocker.request_history:
            my_request = DiscordRequest(r.method, r.url)
            if my_request == modify_guild_member_request and "roles" in r.json():
                roles_updated = True
                self.assertSetEqual(set(r.json()["roles"]), {3, 13, 99})
                break

        self.assertTrue(roles_updated)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))

    def test_when_group_added_to_member_and_role_unknown_then_his_roles_are_updated(
        self, requests_mocker
    ):
        requests_mocker.get(
            guild_member_request.url,
            json=create_discord_guild_member_object(roles=['13', '99'])
        )
        requests_mocker.get(
            guild_roles_request.url,
            json=[ROLE_ALPHA, ROLE_BRAVO, ROLE_MIKE, ROLE_MEMBER]
        )
        requests_mocker.post(create_guild_role_request.url, json=ROLE_CHARLIE)
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)

        # adding new group to trigger signals
        self.user.groups.add(self.group_charlie)
        self.user.refresh_from_db()

        # verify roles for user where updated
        roles_updated = False
        for r in requests_mocker.request_history:
            my_request = DiscordRequest(r.method, r.url)
            if my_request == modify_guild_member_request and "roles" in r.json():
                roles_updated = True
                self.assertSetEqual(set(r.json()["roles"]), {3, 13, 99})
                break

        self.assertTrue(roles_updated)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODULE_PATH + '.managers.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.models.DISCORD_GUILD_ID', TEST_GUILD_ID)
@requests_mock.Mocker()
class TestTasks(NoSocketsTestCase):
    def test_should_update_username(self, requests_mocker):
        # given
        user = create_user()
        discord_user = create_discord_user(user)
        discord_user_obj = create_discord_user_object()
        data = create_discord_guild_member_object(user=discord_user_obj)
        requests_mocker.get(guild_member_request.url, json=data)
        # when
        tasks.update_username.delay(user.pk)
        # then
        discord_user.refresh_from_db()
        self.assertEqual(discord_user.username, discord_user_obj["username"])
        self.assertEqual(
            discord_user.discriminator, discord_user_obj["discriminator"]
        )


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(MODULE_PATH + '.managers.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.models.DISCORD_GUILD_ID', TEST_GUILD_ID)
@requests_mock.Mocker()
class StateTestCase(NoSocketsTestCase):
    fixtures = ['disable_analytics.json']

    def setUp(self):
        clear_cache()
        reset_testdata()

        self.user = AuthUtils.create_user('test_user', disconnect_signals=True)
        AuthUtils.add_main_character(
            self.user,
            'Perm Test Character', '99',
            corp_id='100',
            alliance_id='200',
            corp_name='Perm Test Corp',
            alliance_name='Perm Test Alliance'
        )
        self.test_character = EveCharacter.objects.get(character_id='99')
        self.member_state = State.objects.create(
            name='Test Member',
            priority=150,
        )
        self.access_discord = AuthUtils.get_permission_by_name('discord.access_discord')
        self.member_state.permissions.add(self.access_discord)
        self.member_state.member_characters.add(self.test_character)

    def _add_discord_user(self):
        self.discord_user = DiscordUser.objects.create(
            user=self.user, uid="12345678910"
        )

    def _refresh_user(self):
        self.user = User.objects.get(pk=self.user.pk)

    def test_perm_changes_to_higher_priority_state_creation(self, requests_mocker):
        mock_url = DiscordRequest(
            method='DELETE',
            url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/12345678910'
        )
        requests_mocker.delete(mock_url.url, status_code=204)
        self._add_discord_user()
        self._refresh_user()
        higher_state = State.objects.create(
            name='Higher State',
            priority=200,
        )
        self.assertIsNotNone(self.user.discord)
        higher_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(higher_state, self.user.profile.state)
        with self.assertRaises(DiscordUser.DoesNotExist):
            self.user.discord
        higher_state.member_characters.clear()
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        with self.assertRaises(DiscordUser.DoesNotExist):
            self.user.discord

    def test_perm_changes_to_lower_priority_state_creation(self, requests_mocker):
        mock_url = DiscordRequest(
            method='DELETE',
            url=f'{DISCORD_API_BASE_URL}guilds/{TEST_GUILD_ID}/members/12345678910'
        )
        requests_mocker.delete(mock_url.url, status_code=204)
        self._add_discord_user()
        self._refresh_user()
        lower_state = State.objects.create(
            name='Lower State',
            priority=125,
        )
        self.assertIsNotNone(self.user.discord)
        lower_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        self.member_state.member_characters.clear()
        self._refresh_user()
        self.assertEqual(lower_state, self.user.profile.state)
        with self.assertRaises(DiscordUser.DoesNotExist):
            self.user.discord
        self.member_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        with self.assertRaises(DiscordUser.DoesNotExist):
            self.user.discord


@patch(MODULE_PATH + '.core.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.managers.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.models.DISCORD_GUILD_ID', TEST_GUILD_ID)
@requests_mock.Mocker()
class TestUserFeatures(WebTest):
    fixtures = ['disable_analytics.json']

    def setUp(self):
        clear_cache()
        reset_testdata()
        self.member = AuthUtils.create_member(TEST_USER_NAME)
        AuthUtils.add_main_character_2(
            self.member,
            TEST_MAIN_NAME,
            TEST_MAIN_ID,
            disconnect_signals=True
        )
        add_permissions_to_members()

    @patch(MODULE_PATH + '.views.messages', spec=True)
    @patch(MODULE_PATH + '.managers.OAuth2Session', spec=True)
    def test_user_activation_normal(
        self, requests_mocker, mock_OAuth2Session, mock_messages
    ):
        # setup
        requests_mocker.get(
            guild_infos_request.url, json=create_discord_guild_object()
        )
        requests_mocker.get(
            user_get_current_request.url, json=create_discord_user_object()
        )
        requests_mocker.get(
            guild_roles_request.url, json=[ROLE_ALPHA, ROLE_BRAVO, ROLE_MEMBER]
        )
        requests_mocker.get(
            guild_member_request.url,
            status_code=404,
            json=create_discord_error_response_unknown_member()
        )
        requests_mocker.put(add_guild_member_request.url, status_code=201)

        authentication_code = 'auth_code'
        oauth_url = 'https://www.example.com/oauth'
        state = ''
        mock_OAuth2Session.return_value.authorization_url.return_value = \
            oauth_url, state

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

        # user clicks Discord service activation link on page
        response = services_page.click(href=reverse('discord:activate'))

        # check we got a redirect to Discord OAuth
        self.assertRedirects(
            response, expected_url=oauth_url, fetch_redirect_response=False
        )

        # simulate Discord callback
        response = self.app.get(
            reverse('discord:callback'), params={'code': authentication_code}
        )

        # user got a success message
        self.assertTrue(mock_messages.success.called)
        self.assertFalse(mock_messages.error.called)

        requests_made = list()
        for r in requests_mocker.request_history:
            obj = DiscordRequest(r.method, r.url)
            requests_made.append(obj)
        self.assertIn(add_guild_member_request, requests_made)

    @patch(MODULE_PATH + '.views.messages', spec=True)
    @patch(MODULE_PATH + '.managers.OAuth2Session', spec=True)
    def test_should_activate_existing_user_and_keep_managed_and_reserved_roles(
        self, requests_mocker, mock_OAuth2Session, mock_messages
    ):
        # setup
        requests_mocker.get(
            guild_infos_request.url, json=create_discord_guild_object()
        )
        requests_mocker.get(
            user_get_current_request.url, json=create_discord_user_object()
        )
        requests_mocker.get(
            guild_roles_request.url, json=[
                ROLE_ALPHA, ROLE_CHARLIE, ROLE_MEMBER, ROLE_MIKE
            ]
        )
        requests_mocker.get(
            guild_member_request.url,
            json=create_discord_guild_member_object(roles=[1, 3, 13])
        )
        requests_mocker.patch(modify_guild_member_request.url, status_code=204)
        ReservedGroupName.objects.create(
            name="charlie", reason="dummy", created_by="xyz"
        )

        authentication_code = 'auth_code'
        oauth_url = 'https://www.example.com/oauth'
        state = ''
        mock_OAuth2Session.return_value.authorization_url.return_value = \
            oauth_url, state

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

        # user clicks Discord service activation link on page
        response = services_page.click(href=reverse('discord:activate'))

        # check we got a redirect to Discord OAuth
        self.assertRedirects(
            response, expected_url=oauth_url, fetch_redirect_response=False
        )

        # simulate Discord callback
        response = self.app.get(
            reverse('discord:callback'), params={'code': authentication_code}
        )

        # user got a success message
        self.assertTrue(mock_messages.success.called)
        self.assertFalse(mock_messages.error.called)

        my_request = None
        for r in requests_mocker.request_history:
            obj = DiscordRequest(r.method, r.url, r.text)
            if obj == modify_guild_member_request:
                my_request = obj
                break
        else:
            self.fail("Request not found")
        self.assertSetEqual(set(my_request.json()["roles"]), {3, 13, 99})

    @patch(MODULE_PATH + '.views.messages', spec=True)
    @patch(MODULE_PATH + '.managers.OAuth2Session', spec=True)
    def test_user_activation_failed(
        self, requests_mocker, mock_OAuth2Session, mock_messages
    ):
        # setup
        requests_mocker.get(
            guild_infos_request.url, json=create_discord_guild_object()
        )
        requests_mocker.get(
            user_get_current_request.url, json=create_discord_user_object()
        )
        requests_mocker.get(
            guild_roles_request.url, json=[ROLE_ALPHA, ROLE_BRAVO, ROLE_MEMBER]
        )
        requests_mocker.get(
            guild_member_request.url,
            status_code=404,
            json=create_discord_error_response_unknown_member()
        )

        mock_exception = HTTPError('error')
        mock_exception.response = Mock()
        mock_exception.response.status_code = 503
        requests_mocker.put(add_guild_member_request.url, exc=mock_exception)

        authentication_code = 'auth_code'
        oauth_url = 'https://www.example.com/oauth'
        state = ''
        mock_OAuth2Session.return_value.authorization_url.return_value = \
            oauth_url, state

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

        # click activate on the service page
        response = services_page.click(href=reverse('discord:activate'))

        # check we got a redirect to Discord OAuth
        self.assertRedirects(
            response, expected_url=oauth_url, fetch_redirect_response=False
        )

        # simulate Discord callback
        response = self.app.get(
            reverse('discord:callback'), params={'code': authentication_code}
        )

        # user got a success message
        self.assertFalse(mock_messages.success.called)
        self.assertTrue(mock_messages.error.called)

        requests_made = list()
        for r in requests_mocker.request_history:
            obj = DiscordRequest(r.method, r.url)
            requests_made.append(obj)
        self.assertIn(add_guild_member_request, requests_made)

    @patch(MODULE_PATH + '.views.messages', spec=True)
    def test_user_deactivation_normal(self, requests_mocker, mock_messages):
        # setup
        requests_mocker.get(
            guild_infos_request.url, json=create_discord_guild_object()
        )
        requests_mocker.delete(remove_guild_member_request.url, status_code=204)
        DiscordUser.objects.create(user=self.member, uid=TEST_USER_ID)

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

        # click deactivate on the service page
        response = services_page.click(href=reverse('discord:deactivate'))

        # check we got a redirect to service page
        self.assertRedirects(response, expected_url=reverse('services:services'))

        # user got a success message
        self.assertTrue(mock_messages.success.called)
        self.assertFalse(mock_messages.error.called)

        requests_made = list()
        for r in requests_mocker.request_history:
            obj = DiscordRequest(r.method, r.url)
            requests_made.append(obj)
        self.assertIn(remove_guild_member_request, requests_made)

    @patch(MODULE_PATH + '.views.messages', spec=True)
    def test_user_deactivation_fails(self, requests_mocker, mock_messages):
        # setup
        requests_mocker.get(
            guild_infos_request.url, json=create_discord_guild_object()
        )
        mock_exception = HTTPError('error')
        mock_exception.response = Mock()
        mock_exception.response.status_code = 503
        requests_mocker.delete(remove_guild_member_request.url, exc=mock_exception)

        DiscordUser.objects.create(user=self.member, uid=TEST_USER_ID)

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

        # click deactivate on the service page
        response = services_page.click(href=reverse('discord:deactivate'))

        # check we got a redirect to service page
        self.assertRedirects(response, expected_url=reverse('services:services'))

        # user got a success message
        self.assertFalse(mock_messages.success.called)
        self.assertTrue(mock_messages.error.called)

        requests_made = list()
        for r in requests_mocker.request_history:
            obj = DiscordRequest(r.method, r.url)
            requests_made.append(obj)
        self.assertIn(remove_guild_member_request, requests_made)

    @patch(MODULE_PATH + '.views.messages', spec=True)
    def test_user_add_new_server(self, requests_mocker, mock_messages):
        # setup
        mock_exception = HTTPError(Mock(**{"response.status_code": 400}))
        requests_mocker.get(guild_infos_request.url, exc=mock_exception)

        # login
        self.member.is_superuser = True
        self.member.is_staff = True
        self.member.save()
        self.app.set_user(self.member)

        # click deactivate on the service page
        response = self.app.get(reverse('services:services'))

        # check we got can see the page and the "link server" button
        self.assertEqual(response.status_int, 200)
        self.assertIsNotNone(response.html.find(id='btnLinkDiscordServer'))

    def test_when_server_name_fails_user_can_still_see_service_page(
        self, requests_mocker
    ):
        # setup
        requests_mocker.get(guild_infos_request.url, exc=DiscordApiBackoff(1000))

        # login
        self.app.set_user(self.member)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)

    @override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    @patch(MODULE_PATH + ".core.default_bot_client", spec=True)
    def test_server_name_is_updated_by_task(
        self, requests_mocker, mock_bot_client
    ):
        # setup
        mock_bot_client.guild_name.return_value = "Test Guild"
        # run task to update usernames
        tasks.update_all_usernames()

        # login
        self.app.set_user(self.member)

        # disable API call to make sure server name is not retrieved from API
        mock_exception = HTTPError(Mock(**{"response.status_code": 400}))
        requests_mocker.get(guild_infos_request.url, exc=mock_exception)

        # user opens services page
        services_page = self.app.get(reverse('services:services'))
        self.assertEqual(services_page.status_code, 200)
        self.assertIn("Test Guild", services_page.text)
