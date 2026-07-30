import urllib
from unittest.mock import Mock, patch

from requests.exceptions import HTTPError

from django.contrib.auth.models import User

from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.testing import NoSocketsTestCase

from ..app_settings import DISCORD_APP_ID, DISCORD_APP_SECRET, DISCORD_CALLBACK_URL
from ..discord_client import (
    DISCORD_OAUTH_BASE_URL,
    DISCORD_OAUTH_TOKEN_URL,
    DiscordApiBackoff,
    DiscordClient,
    RolesSet,
)
from ..discord_client.tests.factories import (
    TEST_GUILD_ID,
    TEST_USER_ID,
    TEST_USER_NAME,
    create_role,
    create_user,
)
from ..models import DiscordUser
from ..utils import set_logger_to_file
from . import MODULE_PATH, TEST_MAIN_NAME

logger = set_logger_to_file(MODULE_PATH + '.managers', __file__)


@patch(MODULE_PATH + '.managers.DISCORD_GUILD_ID', TEST_GUILD_ID)
@patch(MODULE_PATH + '.managers.DiscordClient', spec=DiscordClient)
@patch(MODULE_PATH + '.managers.create_bot_client', spec=True)
@patch(
    MODULE_PATH + '.models.DiscordUser.objects._exchange_auth_code_for_token', spec=True
)
@patch(MODULE_PATH + '.managers.calculate_roles_for_user', spec=True)
@patch(MODULE_PATH + '.managers.user_formatted_nick', spec=True)
class TestAddUser(NoSocketsTestCase):

    def setUp(self):
        self.user = AuthUtils.create_user(TEST_USER_NAME)
        self.access_token = 'accesstoken'

    def test_can_create_user_no_roles_no_nick(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_create_bot_client.return_value.add_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.add_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertEqual(kwargs['access_token'], self.access_token)
        self.assertFalse(kwargs['role_ids'])
        self.assertIsNone(kwargs['nick'])

    def test_can_create_user_with_roles_no_nick(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        role_a = create_role(id=1)
        role_b = create_role(id=2)
        roles_calculated = RolesSet([role_a, role_b])
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = roles_calculated, None
        mock_create_bot_client.return_value.add_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.add_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertEqual(kwargs['access_token'], self.access_token)
        self.assertSetEqual(set(kwargs['role_ids']), {1, 2})
        self.assertIsNone(kwargs['nick'])

    def test_can_activate_existing_user_with_roles_no_nick(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        role_a = create_role(id=1)
        role_b = create_role(id=2)
        roles_calculated = RolesSet([role_a, role_b])
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = roles_calculated, False
        mock_create_bot_client.return_value.add_guild_member.return_value = None
        mock_create_bot_client.return_value.modify_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.modify_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertSetEqual(set(kwargs['role_ids']), {1, 2})
        self.assertIsNone(kwargs['nick'])

    @patch(MODULE_PATH + '.managers.DISCORD_SYNC_NAMES', True)
    def test_can_create_user_no_roles_with_nick(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = TEST_MAIN_NAME
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_create_bot_client.return_value.add_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.add_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertEqual(kwargs['access_token'], self.access_token)
        self.assertFalse(kwargs['role_ids'])
        self.assertEqual(kwargs['nick'], TEST_MAIN_NAME)

    @patch(MODULE_PATH + '.managers.DISCORD_SYNC_NAMES', True)
    def test_can_activate_existing_user_no_roles_with_nick(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = TEST_MAIN_NAME
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), False
        mock_create_bot_client.return_value.add_guild_member.return_value = None
        mock_create_bot_client.return_value.modify_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.modify_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertFalse(kwargs['role_ids'])
        self.assertEqual(kwargs['nick'], TEST_MAIN_NAME)

    @patch(MODULE_PATH + '.managers.DISCORD_SYNC_NAMES', False)
    def test_can_create_user_no_roles_and_without_nick_if_turned_off(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = TEST_MAIN_NAME
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_create_bot_client.return_value.add_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.add_guild_member.call_args
        self.assertEqual(kwargs['guild_id'], TEST_GUILD_ID)
        self.assertEqual(kwargs['user_id'], TEST_USER_ID)
        self.assertEqual(kwargs['access_token'], self.access_token)
        self.assertFalse(kwargs['role_ids'])
        self.assertIsNone(kwargs['nick'])

    def test_can_activate_existing_guild_member(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        roles_calculated = RolesSet([create_role()])
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = roles_calculated, False
        mock_create_bot_client.return_value.add_guild_member.return_value = None
        mock_create_bot_client.return_value.modify_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.modify_guild_member.called)

    def test_can_activate_existing_member_with_roles(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        roles_calculated = RolesSet([create_role(id=1)])
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = roles_calculated, False
        mock_create_bot_client.return_value.add_guild_member.return_value = None
        mock_create_bot_client.return_value.modify_guild_member.return_value = True
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertTrue(result)
        self.assertTrue(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        _, kwargs = mock_create_bot_client.return_value.modify_guild_member.call_args
        self.assertSetEqual(set(kwargs['role_ids']), {1})

    def test_can_activate_existing_guild_member_failure(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        roles_calculated = RolesSet([create_role()])
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = roles_calculated, False
        mock_create_bot_client.return_value.add_guild_member.return_value = None
        mock_create_bot_client.return_value.modify_guild_member.return_value = False
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertFalse(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.modify_guild_member.called)

    def test_return_false_when_user_creation_fails(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_create_bot_client.return_value.add_guild_member.return_value = False
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertFalse(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.add_guild_member.called)

    def test_return_false_when_on_api_backoff(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_create_bot_client.return_value.add_guild_member.side_effect = \
            DiscordApiBackoff(999)
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertFalse(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.add_guild_member.called)

    def test_return_false_on_http_error(
        self,
        mock_user_formatted_nick,
        mock_calculate_roles_for_user,
        mock_exchange_auth_code_for_token,
        mock_create_bot_client,
        mock_DiscordClient,
    ):
        # given
        discord_user = create_user(id=TEST_USER_ID)
        mock_user_formatted_nick.return_value = None
        mock_exchange_auth_code_for_token.return_value = self.access_token
        mock_DiscordClient.return_value.current_user.return_value = discord_user
        mock_calculate_roles_for_user.return_value = RolesSet([]), None
        mock_exception = HTTPError('error')
        mock_exception.response = Mock()
        mock_exception.response.status_code = 500
        mock_create_bot_client.return_value.add_guild_member.side_effect = mock_exception
        # when
        result = DiscordUser.objects.add_user(self.user, authorization_code='abcdef')
        # then
        self.assertFalse(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.add_guild_member.called)


class TestOauthHelpers(NoSocketsTestCase):

    @patch(MODULE_PATH + '.managers.DISCORD_APP_ID', '123456')
    def test_generate_bot_add_url(self):
        bot_add_url = DiscordUser.objects.generate_bot_add_url()

        auth_url = DISCORD_OAUTH_BASE_URL
        real_bot_add_url = (
            f'{auth_url}?client_id=123456&scope=bot'
            f'&permissions={DiscordUser.objects.BOT_PERMISSIONS}'
        )
        self.assertEqual(bot_add_url, real_bot_add_url)

    def test_generate_oauth_redirect_url(self):
        oauth_url = DiscordUser.objects.generate_oauth_redirect_url()

        self.assertIn(DISCORD_OAUTH_BASE_URL, oauth_url)
        self.assertIn('+'.join(DiscordUser.objects.SCOPES), oauth_url)
        self.assertIn(DISCORD_APP_ID, oauth_url)
        self.assertIn(urllib.parse.quote_plus(DISCORD_CALLBACK_URL), oauth_url)

    @patch(MODULE_PATH + '.managers.OAuth2Session', spec=True)
    def test_process_callback_code(self, oauth):
        instance = oauth.return_value
        instance.fetch_token.return_value = {'access_token': 'mywonderfultoken'}

        token = DiscordUser.objects._exchange_auth_code_for_token('12345')

        self.assertTrue(oauth.called)
        args, kwargs = oauth.call_args
        self.assertEqual(args[0], DISCORD_APP_ID)
        self.assertEqual(kwargs['redirect_uri'], DISCORD_CALLBACK_URL)
        self.assertTrue(instance.fetch_token.called)
        args, kwargs = instance.fetch_token.call_args
        self.assertEqual(args[0], DISCORD_OAUTH_TOKEN_URL)
        self.assertEqual(kwargs['client_secret'], DISCORD_APP_SECRET)
        self.assertEqual(kwargs['code'], '12345')
        self.assertEqual(token, 'mywonderfultoken')


class TestUserHasAccount(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_user(TEST_USER_NAME)

    def test_return_true_if_user_has_account(self):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        self.assertTrue(DiscordUser.objects.user_has_account(self.user))

    def test_return_false_if_user_has_no_account(self):
        self.assertFalse(DiscordUser.objects.user_has_account(self.user))

    def test_return_false_if_user_does_not_exist(self):
        my_user = User(username='Dummy')
        my_user.save()
        self.assertFalse(DiscordUser.objects.user_has_account(my_user))

    def test_return_false_if_not_called_with_user_object(self):
        self.assertFalse(DiscordUser.objects.user_has_account('abc'))


class TestOtherMethods(NoSocketsTestCase):
    @patch(MODULE_PATH + '.managers.core_group_to_role', spec=True)
    def test_should_call_group_to_role(self, mock_core_group_to_role):
        # given
        role = create_role(id=1, name="alpha", managed=False)
        mock_core_group_to_role.return_value = role
        # when
        result = DiscordUser.objects.group_to_role(Mock())
        # then
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "alpha")
        self.assertEqual(result["managed"], False)

    @patch(MODULE_PATH + '.managers.core_server_name', spec=True)
    def test_should_call_server_name(self, mock_core_server_name):
        # when
        DiscordUser.objects.server_name()
        # then
        self.assertTrue(mock_core_server_name.called)
