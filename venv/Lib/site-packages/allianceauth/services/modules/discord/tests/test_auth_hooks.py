from unittest.mock import patch

from django.test import RequestFactory
from django.test.utils import override_settings

from allianceauth.notifications.models import Notification
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.utils.testing import NoSocketsTestCase

from ..auth_hooks import DiscordService
from ..discord_client.tests.factories import TEST_USER_ID, TEST_USER_NAME
from ..models import DiscordUser
from ..utils import set_logger_to_file
from . import MODULE_PATH, add_permissions_to_members

logger = set_logger_to_file(MODULE_PATH + '.auth_hooks', __file__)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestDiscordService(NoSocketsTestCase):

    def setUp(self):
        self.member = AuthUtils.create_member(TEST_USER_NAME)
        DiscordUser.objects.create(
            user=self.member,
            uid=TEST_USER_ID,
            username=TEST_USER_NAME,
            discriminator='1234'
        )
        self.none_member = AuthUtils.create_user('Lex Luther')
        self.service = DiscordService
        add_permissions_to_members()
        self.factory = RequestFactory()
        Notification.objects.all().delete()

    def test_service_enabled(self):
        service = self.service()
        self.assertTrue(service.service_active_for_user(self.member))
        self.assertFalse(service.service_active_for_user(self.none_member))

    @patch(MODULE_PATH + '.tasks.update_all_groups')
    def test_update_all_groups(self, mock_update_all_groups):
        service = self.service()
        service.update_all_groups()
        self.assertTrue(mock_update_all_groups.delay.called)

    @patch(MODULE_PATH + '.tasks.update_groups_bulk')
    def test_update_groups_bulk(self, mock_update_groups_bulk):
        service = self.service()
        service.update_groups_bulk([self.member])
        self.assertTrue(mock_update_groups_bulk.delay.called)

    @patch(MODULE_PATH + '.tasks.update_groups')
    def test_update_groups_for_member(self, mock_update_groups):
        service = self.service()
        service.update_groups(self.member)
        self.assertTrue(mock_update_groups.apply_async.called)

    @patch(MODULE_PATH + '.tasks.update_groups')
    def test_update_groups_for_none_member(self, mock_update_groups):
        service = self.service()
        service.update_groups(self.none_member)
        self.assertFalse(mock_update_groups.apply_async.called)

    @patch(MODULE_PATH + '.models.notify')
    @patch(MODULE_PATH + '.tasks.DiscordUser')
    @patch(MODULE_PATH + '.models.create_bot_client')
    def test_validate_user(
        self, mock_create_bot_client, mock_DiscordUser, mock_notify
    ):
        mock_create_bot_client.return_value.remove_guild_member.return_value = True

        # Test member is not deleted
        service = self.service()
        service.validate_user(self.member)
        self.assertTrue(DiscordUser.objects.filter(user=self.member).exists())

        # Test none member is deleted
        DiscordUser.objects.create(user=self.none_member, uid=TEST_USER_ID)
        service.validate_user(self.none_member)
        self.assertFalse(DiscordUser.objects.filter(user=self.none_member).exists())

    @patch(MODULE_PATH + '.tasks.update_nickname')
    @patch(MODULE_PATH + '.auth_hooks.DISCORD_SYNC_NAMES', True)
    def test_sync_nickname(self, mock_update_nickname):
        service = self.service()
        service.sync_nickname(self.member)
        self.assertTrue(mock_update_nickname.apply_async.called)

    @patch(MODULE_PATH + '.tasks.update_nickname')
    def test_sync_nickname_no_setting(self, mock_update_nickname):
        service = self.service()
        service.sync_nickname(self.member)
        self.assertFalse(mock_update_nickname.apply_async.called)

    @patch(MODULE_PATH + '.tasks.update_nicknames_bulk')
    def test_sync_nicknames_bulk(self, mock_update_nicknames_bulk):
        service = self.service()
        service.sync_nicknames_bulk([self.member])
        self.assertTrue(mock_update_nicknames_bulk.delay.called)

    @patch(MODULE_PATH + '.models.create_bot_client')
    def test_delete_user_is_member(self, mock_create_bot_client):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = True
        service = self.service()
        # when
        service.delete_user(self.member, notify_user=True)
        # then
        self.assertTrue(mock_create_bot_client.return_value.remove_guild_member.called)
        self.assertFalse(DiscordUser.objects.filter(user=self.member).exists())
        self.assertTrue(Notification.objects.filter(user=self.member).exists())

    @patch(MODULE_PATH + '.models.create_bot_client')
    def test_delete_user_is_not_member(self, mock_create_bot_client):
        # given
        mock_create_bot_client.return_value.remove_guild_member.return_value = True
        service = self.service()
        # when
        service.delete_user(self.none_member)
        # then
        self.assertFalse(mock_create_bot_client.return_value.remove_guild_member.called)

    @patch(MODULE_PATH + '.auth_hooks.server_name')
    def test_render_services_ctrl_with_username(self, mock_server_name):
        # given
        mock_server_name.return_value = "My server"
        service = self.service()
        request = self.factory.get('/services/')
        request.user = self.member
        # when
        response = service.render_services_ctrl(request)
        # then
        self.assertTemplateUsed(service.service_ctrl_template)
        self.assertIn('/discord/reset/', response)
        self.assertIn('/discord/deactivate/', response)

        # Test register becomes available
        self.member.discord.delete()
        self.member.refresh_from_db()
        request.user = self.member
        response = service.render_services_ctrl(request)
        self.assertIn('/discord/activate/', response)

    @patch(MODULE_PATH + '.auth_hooks.server_name')
    def test_render_services_ctrl_wo_username(self, mock_server_name):
        # given
        mock_server_name.return_value = "My server"
        my_member = AuthUtils.create_member('John Doe')
        DiscordUser.objects.create(user=my_member, uid=111222333)
        service = self.service()
        request = self.factory.get('/services/')
        request.user = my_member
        # when
        response = service.render_services_ctrl(request)
        # then
        self.assertTemplateUsed(service.service_ctrl_template)
        self.assertIn('/discord/reset/', response)
        self.assertIn('/discord/deactivate/', response)

    def test_new_discord_username_format(self):
        """
        Test if we get Discord's new username format
        :return:
        :rtype:
        """

        # given
        username = 'william_riker'
        discriminator = '0'  # Seems to be returned as 0 for Discord's new username format

        # when
        discord_username = DiscordService.get_discord_username(
            username=username, discriminator=discriminator
        )

        # then
        expected_username = '@william_riker'
        self.assertEqual(first=discord_username, second=expected_username)
