from django.utils.timezone import now

from allianceauth.authentication.backends import StateBackend
from allianceauth.tests.auth_utils import AuthUtils

from ..discord_client.tests.factories import (
    TEST_USER_DISCRIMINATOR,
    TEST_USER_ID,
    TEST_USER_NAME,
)
from ..models import DiscordUser


def create_user(**kwargs):
    params = {"username": TEST_USER_NAME}
    params.update(kwargs)
    username = StateBackend.iterate_username(params["username"])
    user = AuthUtils.create_user(username)
    return AuthUtils.add_permission_to_user_by_name("discord.access_discord", user)


def create_discord_user(user=None, **kwargs):
    params = {
        "user": user or create_user(),
        "uid": TEST_USER_ID,
        "username": TEST_USER_NAME,
        "discriminator": TEST_USER_DISCRIMINATOR,
        "activated": now(),
    }
    params.update(kwargs)
    return DiscordUser.objects.create(**params)
