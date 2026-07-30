import logging
from typing import ClassVar, Optional

from requests.exceptions import HTTPError

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy

from allianceauth.notifications import notify

from . import __title__
from .app_settings import DISCORD_GUILD_ID
from .core import (
    create_bot_client,
    default_bot_client,
    calculate_roles_for_user,
    user_formatted_nick
)
from .discord_client import DiscordApiBackoff
from .managers import DiscordUserManager
from .utils import LoggerAddTag


logger = LoggerAddTag(logging.getLogger(__name__), __title__)


class DiscordUser(models.Model):
    """The Discord user account of an Auth user."""

    user = models.OneToOneField(
        User,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='discord',
        help_text='Auth user owning this Discord account'
    )
    uid = models.BigIntegerField(
        db_index=True,
        help_text='user\'s ID on Discord'
    )
    username = models.CharField(
        max_length=32,
        default='',
        blank=True,
        db_index=True,
        help_text='user\'s username on Discord'
    )
    discriminator = models.CharField(
        max_length=4,
        default='',
        blank=True,
        help_text='user\'s discriminator on Discord'
    )
    activated = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        help_text='Date & time this service account was activated'
    )

    objects: ClassVar[DiscordUserManager] = DiscordUserManager()

    class Meta:
        permissions = (
            ("access_discord", "Can access the Discord service"),
        )

    def __str__(self):
        return f'{self.user.username} - {self.uid}'

    def __repr__(self):
        return f'{type(self).__name__}(user=\'{self.user}\', uid={self.uid})'

    def update_nickname(self, nickname: str = None) -> bool:
        """Update nickname with formatted name of main character

        Params:
        - nickname: optional nickname to be used instead of user's main

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        - False on error or raises exception
        """
        if not nickname:
            nickname = user_formatted_nick(self.user)
        if not nickname:
            return False
        success = default_bot_client.modify_guild_member(
            guild_id=DISCORD_GUILD_ID,
            user_id=self.uid,
            nick=nickname
        )
        if success:
            logger.info('Nickname for %s has been updated', self.user)
        else:
            logger.warning('Failed to update nickname for %s', self.user)
        return success

    def update_groups(self, state_name: str = None) -> Optional[bool]:
        """update groups for a user based on his current group memberships.
        Will add or remove roles of a user as needed.

        Params:
        - state_name: optional state name to be used

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        - False on error or raises exception
        """
        new_roles, is_changed = calculate_roles_for_user(
            user=self.user,
            client=default_bot_client,
            discord_uid=self.uid,
            state_name=state_name
        )
        if is_changed is None:
            logger.debug('User is not a member of this guild %s', self.user)
            return None
        if is_changed:
            logger.debug('Need to update roles for user %s', self.user)
            success = default_bot_client.modify_guild_member(
                guild_id=DISCORD_GUILD_ID,
                user_id=self.uid,
                role_ids=list(new_roles.ids())
            )
            if success:
                logger.info('Roles for %s have been updated', self.user)
            else:
                logger.warning('Failed to update roles for %s', self.user)
            return success
        logger.info('No need to update roles for user %s', self.user)
        return True

    def update_username(self) -> Optional[bool]:
        """Updates the username incl. the discriminator
        from the Discord server and saves it

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        """
        member_info = default_bot_client.guild_member(
            guild_id=DISCORD_GUILD_ID, user_id=self.uid
        )
        if not member_info:
            logger.warning('%s: User not a guild member', self.user)
            return None
        self.username = member_info.user.username
        self.discriminator = member_info.user.discriminator
        self.save()
        logger.info('%s: Username has been updated', self.user)
        return True

    def delete_user(
        self,
        notify_user: bool = False,
        is_rate_limited: bool = True,
        handle_api_exceptions: bool = False
    ) -> Optional[bool]:
        """Deletes the Discount user both on the server and locally

        Params:
        - notify_user: When True will sent a notification to the user
        informing him about the deleting of his account
        - is_rate_limited: When False will disable default rate limiting (use with care)
        - handle_api_exceptions: When True method will return False
        when an API exception occurs

        Returns True when successful, otherwise False or raises exceptions
        Return None if user does no longer exist
        """
        try:
            _user = self.user
            client = create_bot_client(is_rate_limited=is_rate_limited)
            success = client.remove_guild_member(
                guild_id=DISCORD_GUILD_ID, user_id=self.uid
            )
            if success is not False:
                deleted_count, _ = self.delete()
                if deleted_count > 0:
                    if notify_user:
                        notify(
                            user=_user,
                            title=gettext_lazy('Discord Account Disabled'),
                            message=gettext_lazy(
                                'Your Discord account was disabled automatically '
                                'by Auth. If you think this was a mistake, '
                                'please contact an admin.'
                            ),
                            level='warning'
                        )
                    logger.info('Account for user %s was deleted.', _user)
                    return True
                logger.debug('Account for user %s was already deleted.', _user)
                return None

            logger.warning(
                'Failed to remove user %s from the Discord server', _user
            )
            return False

        except (HTTPError, ConnectionError, DiscordApiBackoff) as ex:
            if handle_api_exceptions:
                logger.exception(
                    'Failed to remove user %s from Discord server: %s',self.user, ex
                )
                return False
            raise ex
