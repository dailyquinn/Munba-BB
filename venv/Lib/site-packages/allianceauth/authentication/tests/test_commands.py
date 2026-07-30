from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from allianceauth.tests.auth_utils import AuthUtils

from ..models import CharacterOwnership, UserProfile


class ManagementCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('test user', disconnect_signals=True)
        AuthUtils.add_main_character(cls.user, 'test character', '1', '2', 'test corp', 'test')
        character = UserProfile.objects.get(user=cls.user).main_character
        CharacterOwnership.objects.create(user=cls.user, character=character, owner_hash='test')

    def setUp(self):
        self.stdout = StringIO()

    def test_ownership(self):
        call_command('checkmains', stdout=self.stdout)
        self.assertFalse(UserProfile.objects.filter(main_character__isnull=True).count())
        self.assertNotIn(self.user.username, self.stdout.getvalue())
        self.assertIn('All main characters', self.stdout.getvalue())

    def test_no_ownership(self):
        user = AuthUtils.create_user('v1 user', disconnect_signals=True)
        AuthUtils.add_main_character(user, 'v1 character', '10', '20', 'test corp', 'test')
        self.assertFalse(UserProfile.objects.filter(main_character__isnull=True).count())

        call_command('checkmains', stdout=self.stdout)
        self.assertEqual(UserProfile.objects.filter(main_character__isnull=True).count(), 1)
        self.assertIn(user.username, self.stdout.getvalue())
