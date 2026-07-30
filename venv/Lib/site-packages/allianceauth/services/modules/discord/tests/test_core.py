from unittest.mock import Mock, patch

from requests.exceptions import HTTPError

from django.contrib.auth.models import Group

from allianceauth.groupmanagement.models import ReservedGroupName
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.testing import NoSocketsTestCase

from ..core import (
    _user_group_names,
    calculate_roles_for_user,
    group_to_role,
    server_name,
    user_formatted_nick,
)
from ..discord_client import DiscordApiBackoff, DiscordClient, RolesSet
from ..discord_client.tests.factories import TEST_USER_NAME, create_role
from . import MODULE_PATH, TEST_MAIN_ID, TEST_MAIN_NAME


class TestUserGroupNames(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_1 = Group.objects.create(name="Group 1")
        cls.group_2 = Group.objects.create(name="Group 2")

    def setUp(self):
        self.user = AuthUtils.create_member(TEST_USER_NAME)

    def test_return_groups_and_state_names_for_user(self):
        self.user.groups.add(self.group_1)
        result = _user_group_names(self.user)
        expected = ["Group 1", "Member"]
        self.assertSetEqual(set(result), set(expected))

    def test_return_state_only_if_user_has_no_groups(self):
        result = _user_group_names(self.user)
        expected = ["Member"]
        self.assertSetEqual(set(result), set(expected))


class TestUserFormattedNick(NoSocketsTestCase):
    def setUp(self):
        self.user = AuthUtils.create_user(TEST_USER_NAME)

    def test_return_nick_when_user_has_main(self):
        AuthUtils.add_main_character_2(self.user, TEST_MAIN_NAME, TEST_MAIN_ID)
        result = user_formatted_nick(self.user)
        expected = TEST_MAIN_NAME
        self.assertEqual(result, expected)

    def test_return_none_if_user_has_no_main(self):
        result = user_formatted_nick(self.user)
        self.assertIsNone(result)


@patch(MODULE_PATH + ".core.default_bot_client", spec=True)
class TestRoleForGroup(NoSocketsTestCase):
    def test_return_role_if_found(self, mock_bot_client):
        # given
        role = create_role(name="alpha")
        mock_bot_client.match_role_from_name.side_effect = (
            lambda guild_id, role_name: role if role.name == role_name else None
        )
        group = Group.objects.create(name="alpha")
        # when/then
        self.assertEqual(group_to_role(group), role)

    def test_return_empty_dict_if_not_found(self, mock_bot_client):
        # given
        role = create_role(name="alpha")
        mock_bot_client.match_role_from_name.side_effect = (
            lambda guild_id, role_name: role if role.name == role_name else None
        )
        group = Group.objects.create(name="unknown")
        # when/then
        self.assertIsNone(group_to_role(group))


@patch(MODULE_PATH + ".core.default_bot_client", spec=True)
@patch(MODULE_PATH + ".core.logger", spec=True)
class TestServerName(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_user(TEST_USER_NAME)

    def test_returns_name_when_api_returns_it(self, mock_logger, mock_bot_client):
        # given
        my_server_name = "El Dorado"
        mock_bot_client.guild_name.return_value = my_server_name
        # when
        self.assertEqual(server_name(), my_server_name)
        # then
        self.assertFalse(mock_logger.warning.called)

    def test_returns_empty_string_when_api_throws_http_error(
        self, mock_logger, mock_bot_client
    ):
        mock_exception = HTTPError("Test exception")
        mock_exception.response = Mock(**{"status_code": 440})
        mock_bot_client.guild_name.side_effect = mock_exception

        self.assertEqual(server_name(), "")
        self.assertFalse(mock_logger.warning.called)

    def test_returns_empty_string_when_api_throws_service_error(
        self, mock_logger, mock_bot_client
    ):
        mock_bot_client.guild_name.side_effect = DiscordApiBackoff(1000)

        self.assertEqual(server_name(), "")
        self.assertFalse(mock_logger.warning.called)

    def test_returns_empty_string_when_api_throws_unexpected_error(
        self, mock_logger, mock_bot_client
    ):
        mock_bot_client.guild_name.side_effect = RuntimeError

        self.assertEqual(server_name(), "")
        self.assertTrue(mock_logger.warning.called)


class TestCalculateRolesForUser(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_user(TEST_USER_NAME)

    def test_should_return_roles_for_new_member(self):
        # given
        roles = RolesSet([create_role()])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = RolesSet([])
        my_client.match_or_create_roles_from_names_2.return_value = roles
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertTrue(changed)
        self.assertEqual(roles_calculated, roles)

    def test_should_return_changed_roles_for_existing_member(self):
        # given
        role_a = create_role()
        role_b = create_role()
        roles_current = RolesSet([role_a])
        roles_matching = RolesSet([role_a, role_b])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = roles_current
        my_client.match_or_create_roles_from_names_2.return_value = roles_matching
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertTrue(changed)
        self.assertEqual(roles_calculated, roles_matching)

    def test_should_indicate_when_roles_are_unchanged(self):
        # given
        role_a = create_role()
        roles_current = RolesSet([role_a])
        roles_matching = RolesSet([role_a])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = roles_current
        my_client.match_or_create_roles_from_names_2.return_value = roles_matching
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertFalse(changed)
        self.assertEqual(roles_calculated, roles_matching)

    def test_should_indicate_when_user_is_no_guild_member(self):
        # given
        role_a = create_role()
        roles_matching = RolesSet([role_a])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = None
        my_client.match_or_create_roles_from_names_2.return_value = roles_matching
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertIsNone(changed)
        self.assertEqual(roles_calculated, roles_matching)

    def test_should_preserve_managed_roles_for_existing_member(self):
        # given
        role_a = create_role()
        role_b = create_role()
        role_m = create_role(managed=True)
        roles_current = RolesSet([role_a, role_m])
        roles_matching = RolesSet([role_b])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = roles_current
        my_client.match_or_create_roles_from_names_2.return_value = roles_matching
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertTrue(changed)
        self.assertEqual(roles_calculated, RolesSet([role_b, role_m]))

    def test_should_preserve_reserved_roles_for_existing_member(self):
        # given
        role_a = create_role()
        role_b = create_role()
        role_c1 = create_role(name="charlie")
        role_c2 = create_role(name="Charlie")
        roles_current = RolesSet([role_a, role_c1, role_c2])
        roles_matching = RolesSet([role_b])
        my_client = Mock(spec=DiscordClient)
        my_client.guild_member_roles.return_value = roles_current
        my_client.match_or_create_roles_from_names_2.return_value = roles_matching
        ReservedGroupName.objects.create(
            name="charlie", reason="dummy", created_by="xyz"
        )
        # when
        roles_calculated, changed = calculate_roles_for_user(self.user, my_client, 42)
        # then
        self.assertTrue(changed)
        self.assertEqual(roles_calculated, RolesSet([role_b, role_c1, role_c2]))
