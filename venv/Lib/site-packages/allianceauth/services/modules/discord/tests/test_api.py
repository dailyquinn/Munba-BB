from unittest.mock import patch

from allianceauth.utils.testing import NoSocketsTestCase

from ..api import discord_guild_id
from . import MODULE_PATH


class TestDiscordGuildId(NoSocketsTestCase):
    @patch(MODULE_PATH + ".api.DISCORD_GUILD_ID", "123")
    def test_should_return_guild_id_when_configured(self):
        self.assertEqual(discord_guild_id(), 123)

    @patch(MODULE_PATH + ".api.DISCORD_GUILD_ID", "")
    def test_should_return_none_when_not_configured(self):
        self.assertIsNone(discord_guild_id())
