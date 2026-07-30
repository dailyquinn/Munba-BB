from django.contrib.auth.models import Group

from allianceauth.tests.auth_utils import AuthUtils

DEFAULT_AUTH_GROUP = 'Member'
MODULE_PATH = 'allianceauth.services.modules.discord'

TEST_MAIN_NAME = 'Spiderman'
TEST_MAIN_ID = 1005


def add_permissions_to_members():
    permission = AuthUtils.get_permission_by_name('discord.access_discord')
    members = Group.objects.get_or_create(name=DEFAULT_AUTH_GROUP)[0]
    AuthUtils.add_permissions_to_groups([permission], [members])
