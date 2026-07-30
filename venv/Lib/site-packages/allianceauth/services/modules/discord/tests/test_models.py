from unittest.mock import Mock, patch

from requests.exceptions import HTTPError

from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.testing import NoSocketsTestCase

from ..discord_client import DiscordApiBackoff, RolesSet
from ..discord_client.tests.factories import (
    TEST_USER_ID,
    TEST_USER_NAME,
    create_guild_member,
    create_role,
)
from ..discord_client.tests.factories import create_user as create_guild_user
from ..models import DiscordUser
from ..utils import set_logger_to_file
from . import MODULE_PATH, TEST_MAIN_ID, TEST_MAIN_NAME
from .factories import create_discord_user, create_user

logger = set_logger_to_file(MODULE_PATH + '.models', __file__)


class TestBasicsAndHelpers(NoSocketsTestCase):

    def test_str(self):
        user = AuthUtils.create_user(TEST_USER_NAME)
        discord_user = DiscordUser.objects.create(user=user, uid=TEST_USER_ID)
        expected = 'Peter Parker - 198765432012345678'
        self.assertEqual(str(discord_user), expected)

    def test_repr(self):
        user = AuthUtils.create_user(TEST_USER_NAME)
        discord_user = DiscordUser.objects.create(user=user, uid=TEST_USER_ID)
        expected = 'DiscordUser(user=\'Peter Parker\', uid=198765432012345678)'
        self.assertEqual(repr(discord_user), expected)


@patch(MODULE_PATH + '.models.default_bot_client', spec=True)
class TestUpdateNick(NoSocketsTestCase):

    def setUp(self):
        self.user = AuthUtils.create_user(TEST_USER_NAME)
        self.discord_user = DiscordUser.objects.create(
            user=self.user, uid=TEST_USER_ID
        )

    def test_can_update(self, mock_default_bot_client):
        # given
        AuthUtils.add_main_character_2(
            self.user, TEST_MAIN_NAME, TEST_MAIN_ID, disconnect_signals=True
        )
        mock_default_bot_client.modify_guild_member.return_value = True
        # when
        result = self.discord_user.update_nickname()
        # then
        self.assertTrue(result)
        self.assertTrue(mock_default_bot_client.modify_guild_member.called)

    def test_dont_update_if_user_has_no_main(self, mock_default_bot_client):
        # given
        mock_default_bot_client.modify_guild_member.return_value = False
        # when
        result = self.discord_user.update_nickname()
        # then
        self.assertFalse(result)
        self.assertFalse(mock_default_bot_client.modify_guild_member.called)

    def test_return_none_if_user_no_longer_a_member(self, mock_default_bot_client):
        # given
        AuthUtils.add_main_character_2(
            self.user, TEST_MAIN_NAME, TEST_MAIN_ID, disconnect_signals=True
        )
        mock_default_bot_client.modify_guild_member.return_value = None
        # when
        result = self.discord_user.update_nickname()
        # then
        self.assertIsNone(result)
        self.assertTrue(mock_default_bot_client.modify_guild_member.called)

    def test_return_false_if_api_returns_false(self, mock_default_bot_client):
        # given
        AuthUtils.add_main_character_2(
            self.user, TEST_MAIN_NAME, TEST_MAIN_ID, disconnect_signals=True
        )
        mock_default_bot_client.modify_guild_member.return_value = False
        # when
        result = self.discord_user.update_nickname()
        # then
        self.assertFalse(result)
        self.assertTrue(mock_default_bot_client.modify_guild_member.called)


@patch(MODULE_PATH + '.models.default_bot_client.guild_member', spec=True)
class TestUpdateUsername(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = create_user()

    def test_can_update(self, mock_guild_member):
        # given
        discord_user = create_discord_user(user=self.user)
        new_username = 'New name'
        new_discriminator = '9876'
        guild_user = create_guild_user(
            username='New name', discriminator=new_discriminator
        )
        mock_guild_member.return_value = create_guild_member(user=guild_user)
        # when
        result = discord_user.update_username()
        # then
        self.assertTrue(result)
        self.assertTrue(mock_guild_member.called)
        discord_user.refresh_from_db()
        self.assertEqual(discord_user.username, new_username)
        self.assertEqual(discord_user.discriminator, new_discriminator)

    def test_return_none_if_user_no_longer_a_member(self, mock_guild_member):
        # given
        discord_user = create_discord_user(user=self.user)
        mock_guild_member.return_value = None
        # when
        result = discord_user.update_username()
        # then
        self.assertIsNone(result)
        self.assertTrue(mock_guild_member.called)


@patch(MODULE_PATH + '.models.notify', spec=True)
@patch(MODULE_PATH + '.models.create_bot_client', spec=True)
class TestDeleteUser(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_user(TEST_USER_NAME)

    def setUp(self):
        self.discord_user = DiscordUser.objects.create(
            user=self.user, uid=TEST_USER_ID
        )

    def test_can_delete_user(self, mock_create_bot_client, mock_notify):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = True
        # when
        result = self.discord_user.delete_user()
        # then
        self.assertTrue(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.remove_guild_member.called)
        self.assertFalse(mock_notify.called)

    def test_can_delete_user_and_notify_user(self, mock_create_bot_client, mock_notify):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = True
        # when
        result = self.discord_user.delete_user(notify_user=True)
        # then
        self.assertTrue(result)
        self.assertTrue(mock_notify.called)

    def test_can_delete_user_when_member_is_unknown(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = None
        # when
        result = self.discord_user.delete_user()
        # then
        self.assertTrue(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.remove_guild_member.called)
        self.assertFalse(mock_notify.called)

    def test_return_false_when_api_fails(self, mock_create_bot_client, mock_notify):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = False
        # when
        result = self.discord_user.delete_user()
        # then
        self.assertFalse(result)

    def test_dont_notify_if_user_was_already_deleted_and_return_none(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = None
        DiscordUser.objects.get(pk=self.discord_user.pk).delete()
        # when
        result = self.discord_user.delete_user()
        # then
        self.assertIsNone(result)
        self.assertFalse(
            DiscordUser.objects.filter(user=self.user, uid=TEST_USER_ID).exists()
        )
        self.assertTrue(mock_create_bot_client.return_value.remove_guild_member.called)
        self.assertFalse(mock_notify.called)

    def test_raise_exception_on_api_backoff(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_create_bot_client.return_value.remove_guild_member.side_effect = \
            DiscordApiBackoff(999)
        # when/then
        with self.assertRaises(DiscordApiBackoff):
            self.discord_user.delete_user()

    def test_return_false_on_api_backoff_and_exception_handling_on(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_create_bot_client.return_value.remove_guild_member.side_effect = \
            DiscordApiBackoff(999)
        # when
        result = self.discord_user.delete_user(handle_api_exceptions=True)
        # then
        self.assertFalse(result)

    def test_raise_exception_on_http_error(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_exception = HTTPError('error')
        mock_exception.response = Mock()
        mock_exception.response.status_code = 500
        mock_create_bot_client.return_value.remove_guild_member.side_effect = \
            mock_exception
        # when/then
        with self.assertRaises(HTTPError):
            self.discord_user.delete_user()

    def test_return_false_on_http_error_and_exception_handling_on(
        self, mock_create_bot_client, mock_notify
    ):
        # given
        mock_exception = HTTPError('error')
        mock_exception.response = Mock()
        mock_exception.response.status_code = 500
        mock_create_bot_client.return_value.remove_guild_member.side_effect = \
            mock_exception
        # when
        result = self.discord_user.delete_user(handle_api_exceptions=True)
        # then
        self.assertFalse(result)


@patch(MODULE_PATH + '.models.default_bot_client', spec=True)
@patch(MODULE_PATH + '.models.calculate_roles_for_user', spec=True)
class TestUpdateGroups(NoSocketsTestCase):

    def setUp(self):
        user = AuthUtils.create_user(TEST_USER_NAME)
        self.discord_user = DiscordUser.objects.create(user=user, uid=TEST_USER_ID)

    def test_should_update_when_roles_have_changed(
        self, mock_calculate_roles_for_user, mock_client
    ):
        # given
        mock_calculate_roles_for_user.return_value = RolesSet([create_role()]), True
        mock_client.modify_guild_member.return_value = True
        # when
        result = self.discord_user.update_groups()
        # then
        self.assertTrue(result)
        self.assertTrue(mock_client.modify_guild_member.called)

    def test_should_not_update_when_roles_have_not_changed(
        self, mock_calculate_roles_for_user, mock_client
    ):
        # given
        mock_calculate_roles_for_user.return_value = RolesSet([create_role()]), False
        mock_client.modify_guild_member.return_value = True
        # when
        result = self.discord_user.update_groups()
        # then
        self.assertTrue(result)
        self.assertFalse(mock_client.modify_guild_member.called)

    def test_should_not_update_when_user_not_guild_member(
        self, mock_calculate_roles_for_user, mock_client
    ):
        # given
        mock_calculate_roles_for_user.return_value = RolesSet([create_role()]), None
        mock_client.modify_guild_member.return_value = True
        # when
        result = self.discord_user.update_groups()
        # then
        self.assertIsNone(result)
        self.assertFalse(mock_client.modify_guild_member.called)

    def test_should_return_false_when_update_failed(
        self, mock_calculate_roles_for_user, mock_client
    ):
        # given
        mock_calculate_roles_for_user.return_value = RolesSet([create_role()]), True
        mock_client.modify_guild_member.return_value = False
        # when
        result = self.discord_user.update_groups()
        # then
        self.assertFalse(result)
        self.assertTrue(mock_client.modify_guild_member.called)
