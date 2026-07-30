import logging
from urllib.parse import urlencode

from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session

from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.timezone import now

from . import __title__
from .app_settings import (
    DISCORD_APP_ID,
    DISCORD_APP_SECRET,
    DISCORD_CALLBACK_URL,
    DISCORD_GUILD_ID,
    DISCORD_SYNC_NAMES,
)
from .core import calculate_roles_for_user, create_bot_client
from .core import group_to_role as core_group_to_role
from .core import server_name as core_server_name
from .core import user_formatted_nick
from .discord_client import (
    DISCORD_OAUTH_BASE_URL,
    DISCORD_OAUTH_TOKEN_URL,
    DiscordApiBackoff,
    DiscordClient,
)
from .utils import LoggerAddTag

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


class DiscordUserManager(models.Manager):
    """Manager for DiscordUser"""

    # full server admin
    BOT_PERMISSIONS = 0x00000008

    # get user ID, accept invite
    SCOPES = [
        'identify',
        'guilds.join',
    ]

    def add_user(
        self,
        user: User,
        authorization_code: str,
        is_rate_limited: bool = True
    ) -> bool:
        """adds a new Discord user

        Params:
        - user: Auth user to join
        - authorization_code: authorization code returns from oauth
        - is_rate_limited: When False will disable default rate limiting (use with care)

        Returns: True on success, else False or raises exception
        """
        try:
            nickname = user_formatted_nick(user) if DISCORD_SYNC_NAMES else None
            access_token = self._exchange_auth_code_for_token(authorization_code)
            user_client = DiscordClient(access_token, is_rate_limited=is_rate_limited)
            discord_user = user_client.current_user()
            bot_client = create_bot_client(is_rate_limited=is_rate_limited)
            roles, changed = calculate_roles_for_user(
                user=user, client=bot_client, discord_uid=discord_user.id
            )
            if changed is None:
                # Handle new member
                created = bot_client.add_guild_member(
                    guild_id=DISCORD_GUILD_ID,
                    user_id=discord_user.id,
                    access_token=access_token,
                    role_ids=list(roles.ids()),
                    nick=nickname
                )
                if not created:
                    logger.warning(
                        "Failed to add user %s with Discord ID %s to Discord server",
                        user,
                        discord_user.id,
                    )
                    return False
            else:
                # Handle existing member
                logger.debug(
                    "User %s with Discord ID %s is already a member. Forcing a Refresh",
                    user,
                    discord_user.id,
                )
                # Force an update cause the discord API won't do it for us.
                updated = bot_client.modify_guild_member(
                    guild_id=DISCORD_GUILD_ID,
                    user_id=discord_user.id,
                    role_ids=list(roles.ids()),
                    nick=nickname
                )
                if not updated:
                    # Could not update the new user so fail.
                    logger.warning(
                        "Failed to add user %s with Discord ID %s to Discord server",
                        user,
                        discord_user.id,
                    )
                    return False

            self.update_or_create(
                user=user,
                defaults={
                    'uid': discord_user.id,
                    'username': discord_user.username[:32],
                    'discriminator': discord_user.discriminator[:4],
                    'activated': now()
                }
            )
            logger.info(
                "Added user %s with Discord ID %s to Discord server",
                user,
                discord_user.id
            )
            return True

        except (HTTPError, ConnectionError, DiscordApiBackoff) as ex:
            logger.exception(
                'Failed to add user %s to Discord server: %s', user, ex
            )
            return False

    def user_has_account(self, user: User) -> bool:
        """Returns True if the user has an Discord account, else False

        only checks locally, does not hit the API
        """
        if not isinstance(user, User):
            return False
        return self.filter(user=user).select_related('user').exists()

    @classmethod
    def generate_bot_add_url(cls) -> str:
        params = urlencode({
            'client_id': DISCORD_APP_ID,
            'scope': 'bot',
            'permissions': str(cls.BOT_PERMISSIONS)

        })
        return f'{DISCORD_OAUTH_BASE_URL}?{params}'

    @classmethod
    def generate_oauth_redirect_url(cls) -> str:
        oauth = OAuth2Session(
            DISCORD_APP_ID, redirect_uri=DISCORD_CALLBACK_URL, scope=cls.SCOPES
        )
        url, _ = oauth.authorization_url(DISCORD_OAUTH_BASE_URL)
        return url

    @staticmethod
    def _exchange_auth_code_for_token(authorization_code: str) -> str:
        oauth = OAuth2Session(DISCORD_APP_ID, redirect_uri=DISCORD_CALLBACK_URL)
        token = oauth.fetch_token(
            DISCORD_OAUTH_TOKEN_URL,
            client_secret=DISCORD_APP_SECRET,
            code=authorization_code
        )
        logger.debug("Received token from OAuth")
        return token['access_token']

    @staticmethod
    def group_to_role(group: Group) -> dict:
        """Fetch the Discord role matching the given Django group by name.

        Returns:
            - Discord role as dict
            - empty dict if no matching role found
        """
        role = core_group_to_role(group)
        return role.asdict() if role else dict()

    @staticmethod
    def server_name(use_cache: bool = True) -> str:
        """Fetches the name of the current Discord server.
        This method is kept to ensure backwards compatibility of this API.
        """
        return core_server_name(use_cache)
