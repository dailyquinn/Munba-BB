from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from requests.exceptions import HTTPError

from django.contrib.auth.models import Group
from django.test.utils import override_settings

from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.testing import NoSocketsTestCase

from .. import tasks
from ..discord_client import DiscordApiBackoff
from ..discord_client.tests.factories import TEST_USER_ID, TEST_USER_NAME
from ..models import DiscordUser
from ..utils import set_logger_to_file
from . import TEST_MAIN_ID, TEST_MAIN_NAME

MODULE_PATH = 'allianceauth.services.modules.discord.tasks'
logger = set_logger_to_file(MODULE_PATH, __file__)


@patch(MODULE_PATH + '.DiscordUser.update_groups')
@patch(MODULE_PATH + ".logger")
class TestUpdateGroups(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_member(TEST_USER_NAME)
        cls.group_1 = Group.objects.create(name='Group 1')
        cls.group_2 = Group.objects.create(name='Group 2')
        cls.group_1.user_set.add(cls.user)
        cls.group_2.user_set.add(cls.user)

    def test_can_update_groups(self, mock_logger, mock_update_groups):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        tasks.update_groups(self.user.pk)
        self.assertTrue(mock_update_groups.called)

    def test_no_action_if_user_has_no_discord_account(
        self, mock_logger, mock_update_groups
    ):
        tasks.update_groups(self.user.pk)
        self.assertFalse(mock_update_groups.called)

    def test_retries_on_api_backoff(self, mock_logger, mock_update_groups):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        mock_exception = DiscordApiBackoff(999)
        mock_update_groups.side_effect = mock_exception

        with self.assertRaises(Retry):
            tasks.update_groups(self.user.pk)

    def test_retry_on_http_error_except_404(self, mock_logger, mock_update_groups):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        mock_exception = HTTPError('error')
        mock_exception.response = MagicMock()
        mock_exception.response.status_code = 500
        mock_update_groups.side_effect = mock_exception

        with self.assertRaises(Retry):
            tasks.update_groups(self.user.pk)

        self.assertTrue(mock_logger.warning.called)

    def test_retry_on_http_error_404_when_user_not_deleted(
        self, mock_logger, mock_update_groups
    ):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        mock_exception = HTTPError('error')
        mock_exception.response = MagicMock()
        mock_exception.response.status_code = 404
        mock_update_groups.side_effect = mock_exception

        with self.assertRaises(Retry):
            tasks.update_groups(self.user.pk)

        self.assertTrue(mock_logger.warning.called)

    def test_retry_on_non_http_error(self, mock_logger, mock_update_groups):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        mock_update_groups.side_effect = ConnectionError

        with self.assertRaises(Retry):
            tasks.update_groups(self.user.pk)

        self.assertTrue(mock_logger.warning.called)

    @patch(MODULE_PATH + '.DISCORD_TASKS_MAX_RETRIES', 3)
    def test_log_error_if_retries_exhausted(self, mock_logger, mock_update_groups):
        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        mock_task = MagicMock(**{'request.retries': 3})
        mock_update_groups.side_effect = ConnectionError
        update_groups_inner = tasks.update_groups.__wrapped__.__func__

        update_groups_inner(mock_task, self.user.pk)
        self.assertTrue(mock_logger.error.called)

    @patch(MODULE_PATH + '.delete_user.delay')
    def test_delete_user_if_user_is_no_longer_member_of_discord_server(
        self, mock_delete_user, mock_logger, mock_update_groups
    ):
        mock_update_groups.return_value = None

        DiscordUser.objects.create(user=self.user, uid=TEST_USER_ID)
        tasks.update_groups(self.user.pk)
        self.assertTrue(mock_update_groups.called)
        self.assertTrue(mock_delete_user.called)


@patch(MODULE_PATH + '.DiscordUser.update_nickname')
class TestUpdateNickname(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_member(TEST_USER_NAME)
        AuthUtils.add_main_character_2(
            cls.user,
            TEST_MAIN_NAME,
            TEST_MAIN_ID,
            corp_id='2',
            corp_name='test_corp',
            corp_ticker='TEST',
            disconnect_signals=True
        )
        cls.discord_user = DiscordUser.objects.create(user=cls.user, uid=TEST_USER_ID)

    def test_can_update_nickname(self, mock_update_nickname):
        mock_update_nickname.return_value = True

        tasks.update_nickname(self.user.pk)
        self.assertTrue(mock_update_nickname.called)

    def test_no_action_when_user_had_no_account(self, mock_update_nickname):
        my_user = AuthUtils.create_user('Dummy User')
        mock_update_nickname.return_value = False

        tasks.update_nickname(my_user.pk)
        self.assertFalse(mock_update_nickname.called)

    def test_retries_on_api_backoff(self, mock_update_nickname):
        mock_exception = DiscordApiBackoff(999)
        mock_update_nickname.side_effect = mock_exception

        with self.assertRaises(Retry):
            tasks.update_nickname(self.user.pk)

    def test_retries_on_general_exception(self, mock_update_nickname):
        mock_update_nickname.side_effect = ConnectionError

        with self.assertRaises(Retry):
            tasks.update_nickname(self.user.pk)

    @patch(MODULE_PATH + '.DISCORD_TASKS_MAX_RETRIES', 3)
    def test_log_error_if_retries_exhausted(self, mock_update_nickname):
        mock_task = MagicMock(**{'request.retries': 3})
        mock_update_nickname.side_effect = ConnectionError
        update_nickname_inner = tasks.update_nickname.__wrapped__.__func__

        update_nickname_inner(mock_task, self.user.pk)


@patch(MODULE_PATH + '.DiscordUser.update_username')
class TestUpdateUsername(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_member(TEST_USER_NAME)
        cls.discord_user = DiscordUser.objects.create(user=cls.user, uid=TEST_USER_ID)

    def test_can_update_username(self, mock_update_username):
        mock_update_username.return_value = True

        tasks.update_username(self.user.pk)
        self.assertTrue(mock_update_username.called)


@patch(MODULE_PATH + '.DiscordUser.delete_user')
class TestDeleteUser(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_member(TEST_USER_NAME)
        cls.discord_user = DiscordUser.objects.create(user=cls.user, uid=TEST_USER_ID)

    def test_can_delete_user(self, mock_delete_user):
        mock_delete_user.return_value = True

        tasks.delete_user(self.user.pk)
        self.assertTrue(mock_delete_user.called)

    def test_can_delete_user_with_notify(self, mock_delete_user):
        mock_delete_user.return_value = True

        tasks.delete_user(self.user.pk, notify_user=True)
        self.assertTrue(mock_delete_user.called)
        args, kwargs = mock_delete_user.call_args
        self.assertTrue(kwargs['notify_user'])

    @patch(MODULE_PATH + '.delete_user.delay')
    def test_dont_retry_delete_user_if_user_is_no_longer_member_of_discord_server(
        self, mock_delete_user_delay, mock_delete_user
    ):
        mock_delete_user.return_value = None

        tasks.delete_user(self.user.pk)
        self.assertTrue(mock_delete_user.called)
        self.assertFalse(mock_delete_user_delay.called)


@patch(MODULE_PATH + '.DiscordUser.update_groups')
class TestTaskPerformUserAction(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = AuthUtils.create_member('Peter Parker')
        cls.discord_user = DiscordUser.objects.create(user=cls.user, uid=TEST_USER_ID)

    def test_raise_value_error_on_unknown_method(self, mock_update_groups):
        mock_task = MagicMock(**{'request.retries': 0})

        with self.assertRaises(ValueError):
            tasks._task_perform_user_action(mock_task, self.user.pk, 'invalid_method')

    def test_catch_and_log_unexpected_exceptions(self, mock_update_groups):
        mock_task = MagicMock(**{'request.retries': 0})
        mock_update_groups.side_effect = RuntimeError

        tasks._task_perform_user_action(mock_task, self.user.pk, 'update_groups')


@patch(MODULE_PATH + '.DiscordUser.objects.server_name')
@patch(MODULE_PATH + ".logger")
class TestTaskUpdateServername(NoSocketsTestCase):

    def test_normal(self, mock_logger, mock_server_name):
        tasks.update_servername()
        self.assertTrue(mock_server_name.called)
        self.assertFalse(mock_logger.error.called)
        _, kwargs = mock_server_name.call_args
        self.assertFalse(kwargs["use_cache"])

    def test_retries_on_api_backoff(self, mock_logger, mock_server_name):
        mock_server_name.side_effect = DiscordApiBackoff(999)

        with self.assertRaises(Retry):
            tasks.update_servername()

        self.assertFalse(mock_logger.error.called)

    def test_retry_on_http_error(self, mock_logger, mock_server_name):
        mock_exception = HTTPError(MagicMock(**{"response.status_code": 500}))
        mock_server_name.side_effect = mock_exception

        with self.assertRaises(Retry):
            tasks.update_servername()

        self.assertTrue(mock_logger.warning.called)

    def test_retry_on_connection_error(self, mock_logger, mock_server_name):
        mock_server_name.side_effect = ConnectionError

        with self.assertRaises(Retry):
            tasks.update_servername()

        self.assertTrue(mock_logger.warning.called)

    @patch(MODULE_PATH + '.DISCORD_TASKS_MAX_RETRIES', 3)
    def test_log_error_if_retries_exhausted(self, mock_logger, mock_server_name):
        mock_task = MagicMock(**{'request.retries': 3})
        mock_server_name.side_effect = ConnectionError
        update_groups_inner = tasks.update_servername.__wrapped__.__func__

        update_groups_inner(mock_task)
        self.assertTrue(mock_logger.error.called)


@patch(MODULE_PATH + '.DiscordUser.objects.server_name')
class TestTaskPerformUsersAction(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_raise_value_error_on_unknown_method(self, mock_server_name):
        mock_task = MagicMock(**{'request.retries': 0})

        with self.assertRaises(ValueError):
            tasks._task_perform_users_action(mock_task, 'invalid_method')

    def test_catch_and_log_unexpected_exceptions(self, mock_server_name):
        mock_server_name.side_effect = RuntimeError
        mock_task = MagicMock(**{'request.retries': 0})

        tasks._task_perform_users_action(mock_task, 'server_name')


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestBulkTasks(NoSocketsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = AuthUtils.create_user('Peter Parker')
        cls.user_2 = AuthUtils.create_user('Kara Danvers')
        cls.user_3 = AuthUtils.create_user('Clark Kent')
        DiscordUser.objects.all().delete()

    @patch(MODULE_PATH + '.update_groups.si')
    def test_can_update_groups_for_multiple_users(self, mock_update_groups):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        DiscordUser.objects.create(user=self.user_3, uid=789)
        expected_pks = [du_1.pk, du_2.pk]

        tasks.update_groups_bulk(expected_pks)
        self.assertEqual(mock_update_groups.call_count, 2)
        current_pks = [args[0][0] for args in mock_update_groups.call_args_list]

        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.update_groups.si')
    def test_can_update_all_groups(self, mock_update_groups):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        du_3 = DiscordUser.objects.create(user=self.user_3, uid=789)

        tasks.update_all_groups()
        self.assertEqual(mock_update_groups.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_groups.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.update_nickname.si')
    def test_can_update_nicknames_for_multiple_users(self, mock_update_nickname):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        DiscordUser.objects.create(user=self.user_3, uid=789)
        expected_pks = [du_1.pk, du_2.pk]

        tasks.update_nicknames_bulk(expected_pks)
        self.assertEqual(mock_update_nickname.call_count, 2)
        current_pks = [
            args[0][0] for args in mock_update_nickname.call_args_list
        ]
        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.update_nickname.si')
    def test_can_update_nicknames_for_all_users(self, mock_update_nickname):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid='123')
        du_2 = DiscordUser.objects.create(user=self.user_2, uid='456')
        du_3 = DiscordUser.objects.create(user=self.user_3, uid='789')

        tasks.update_all_nicknames()
        self.assertEqual(mock_update_nickname.call_count, 3)
        current_pks = [
            args[0][0] for args in mock_update_nickname.call_args_list
        ]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.update_username.si')
    def test_can_update_username_for_multiple_users(self, mock_update_username):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        DiscordUser.objects.create(user=self.user_3, uid=789)
        expected_pks = [du_1.pk, du_2.pk]

        tasks.update_usernames_bulk(expected_pks)
        self.assertEqual(mock_update_username.call_count, 2)
        current_pks = [args[0][0] for args in mock_update_username.call_args_list]

        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.update_username')
    @patch(MODULE_PATH + '.update_servername')
    def test_can_update_all_usernames(
        self, mock_update_servername, mock_update_username
    ):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        du_3 = DiscordUser.objects.create(user=self.user_3, uid=789)

        tasks.update_all_usernames()
        self.assertTrue(mock_update_servername.delay.called)
        self.assertEqual(mock_update_username.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_username.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.DISCORD_SYNC_NAMES', True)
    @patch(MODULE_PATH + '.update_nickname')
    @patch(MODULE_PATH + '.update_groups')
    @patch(MODULE_PATH + '.update_username')
    def test_can_update_all_incl_nicknames(
        self, mock_update_usernames, mock_update_groups, mock_update_nickname
    ):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        du_3 = DiscordUser.objects.create(user=self.user_3, uid=789)

        tasks.update_all()
        self.assertEqual(mock_update_groups.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_groups.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

        self.assertEqual(mock_update_nickname.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_nickname.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

        self.assertEqual(mock_update_usernames.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_usernames.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

    @patch(MODULE_PATH + '.DISCORD_SYNC_NAMES', False)
    @patch(MODULE_PATH + '.update_nickname')
    @patch(MODULE_PATH + '.update_groups')
    @patch(MODULE_PATH + '.update_username')
    def test_can_update_all_excl_nicknames(
        self, mock_update_usernames, mock_update_groups, mock_update_nickname
    ):
        du_1 = DiscordUser.objects.create(user=self.user_1, uid=123)
        du_2 = DiscordUser.objects.create(user=self.user_2, uid=456)
        du_3 = DiscordUser.objects.create(user=self.user_3, uid=789)

        tasks.update_all()
        self.assertEqual(mock_update_groups.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_groups.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))

        self.assertEqual(mock_update_nickname.si.call_count, 0)

        self.assertEqual(mock_update_usernames.si.call_count, 3)
        current_pks = [args[0][0] for args in mock_update_usernames.si.call_args_list]
        expected_pks = [du_1.pk, du_2.pk, du_3.pk]
        self.assertSetEqual(set(current_pks), set(expected_pks))
