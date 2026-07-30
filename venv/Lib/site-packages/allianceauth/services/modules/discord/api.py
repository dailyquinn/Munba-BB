"""Public interface for community apps who want to interact with the Discord server
of the current Alliance Auth instance.

Example
=======

Here is an example for using the api to fetch the current roles from the configured Discord server.

.. code-block:: python

    from allianceauth.services.modules.discord.api import create_bot_client, discord_guild_id

    client = create_bot_client()  # create a new Discord client
    guild_id = discord_guild_id()  # get the ID of the configured Discord server
    roles = client.guild_roles(guild_id)  # fetch the roles from our Discord server

.. seealso::
    The docs for the client class can be found here: :py:class:`~allianceauth.services.modules.discord.discord_client.client.DiscordClient`
"""

from typing import Optional

from .app_settings import DISCORD_GUILD_ID
from .core import create_bot_client, group_to_role, server_name  # noqa
from .discord_client.models import Role  # noqa
from .models import DiscordUser  # noqa

__all__ = ["create_bot_client", "group_to_role", "server_name", "DiscordUser", "Role"]


def discord_guild_id() -> Optional[int]:
    """Guild ID of configured Discord server.

    Returns:
        Guild ID or ``None`` if not configured
    """
    return int(DISCORD_GUILD_ID) if DISCORD_GUILD_ID else None
