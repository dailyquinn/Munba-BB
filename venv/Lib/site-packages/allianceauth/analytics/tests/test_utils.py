from django.apps import apps
from allianceauth.authentication.models import User
from esi.models import Token
from allianceauth.analytics.utils import install_stat_users, install_stat_tokens, install_stat_addons

from django.test.testcases import TestCase


def create_testdata():
    User.objects.all().delete()
    User.objects.create_user(
        'user_1'
        'abc@example.com',
        'password'
    )
    User.objects.create_user(
        'user_2'
        'abc@example.com',
        'password'
    )
    # Token.objects.all().delete()
    # Token.objects.create(
    #            character_id=101,
    #            character_name='character1',
    #            access_token='my_access_token'
    # )
    # Token.objects.create(
    #            character_id=102,
    #            character_name='character2',
    #            access_token='my_access_token'
    # )


class TestAnalyticsUtils(TestCase):

    def test_install_stat_users(self):
        create_testdata()
        expected = 2

        users = install_stat_users()
        self.assertEqual(users, expected)

    # def test_install_stat_tokens(self):
    #    create_testdata()
    #    expected = 2
    #
    #   tokens = install_stat_tokens()
    #   self.assertEqual(tokens, expected)

    def test_install_stat_addons(self):
        # this test does what its testing...
        # but helpful for existing as a sanity check
        expected = len(list(apps.get_app_configs()))
        addons = install_stat_addons()
        self.assertEqual(addons, expected)
