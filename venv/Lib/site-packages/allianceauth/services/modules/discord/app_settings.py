from .utils import clean_setting


DISCORD_APP_ID = clean_setting('DISCORD_APP_ID', '')
"""App ID for the AA bot on Discord. Needs to be set."""

DISCORD_APP_SECRET = clean_setting('DISCORD_APP_SECRET', '')
"""App secret for the AA bot on Discord. Needs to be set."""

DISCORD_BOT_TOKEN = clean_setting('DISCORD_BOT_TOKEN', '')
"""Token used by the AA bot on Discord.  Needs to be set."""

DISCORD_CALLBACK_URL = clean_setting('DISCORD_CALLBACK_URL', '')
"""Callback URL for OAuth with Discord. Needs to be set."""

DISCORD_GUILD_ID = clean_setting('DISCORD_GUILD_ID', '')
"""ID of the Discord Server. Needs to be set."""

DISCORD_TASKS_MAX_RETRIES = clean_setting('DISCORD_TASKS_MAX_RETRIES', 3)
"""Max retries of tasks after an error occurred."""

DISCORD_TASKS_RETRY_PAUSE = clean_setting('DISCORD_TASKS_RETRY_PAUSE', 60)
"""Pause in seconds until next retry for tasks after the API returned an error."""

DISCORD_SYNC_NAMES = clean_setting('DISCORD_SYNC_NAMES', False)
"""Automatically sync Discord users names to user's main character name when created."""
