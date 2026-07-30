from django.contrib.auth.models import User, Group
from django.test import TestCase

from allianceauth.eveonline.models import EveCharacter
from allianceauth.tests.auth_utils import AuthUtils

from esi.models import Token

from ..backends import StateBackend
from ..models import CharacterOwnership, UserProfile, OwnershipRecord

MODULE_PATH = 'allianceauth.authentication'

PERMISSION_1 = "authentication.add_user"
PERMISSION_2 = "authentication.change_user"


class TestStatePermissions(TestCase):

    def setUp(self):
        # permissions
        self.permission_1 = AuthUtils.get_permission_by_name(PERMISSION_1)
        self.permission_2 = AuthUtils.get_permission_by_name(PERMISSION_2)

        # group
        self.group_1 = Group.objects.create(name="Group 1")
        self.group_2 = Group.objects.create(name="Group 2")

        # state
        self.state_1 = AuthUtils.get_member_state()
        self.state_2 = AuthUtils.create_state("Other State", 75)

        # user
        self.user = AuthUtils.create_user("Bruce Wayne")
        self.main = AuthUtils.add_main_character_2(self.user, self.user.username, 123)

    def test_user_has_user_permissions(self):
        self.user.user_permissions.add(self.permission_1)

        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.has_perm(PERMISSION_1))

    def test_user_has_group_permissions(self):
        self.group_1.permissions.add(self.permission_1)
        self.user.groups.add(self.group_1)

        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.has_perm(PERMISSION_1))

    def test_user_has_state_permissions(self):
        self.state_1.permissions.add(self.permission_1)
        self.state_1.member_characters.add(self.main)
        user = User.objects.get(pk=self.user.pk)

        self.assertTrue(user.has_perm(PERMISSION_1))

    def test_when_user_changes_state_perms_change_accordingly(self):
        self.state_1.permissions.add(self.permission_1)
        self.state_1.member_characters.add(self.main)
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.has_perm(PERMISSION_1))

        self.state_2.permissions.add(self.permission_2)
        self.state_2.member_characters.add(self.main)
        self.state_1.member_characters.remove(self.main)
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.has_perm(PERMISSION_1))
        self.assertTrue(user.has_perm(PERMISSION_2))

    def test_state_permissions_are_returned_for_current_user_object(self):
        # verify state permissions are returns for the current user object
        # and not for it's instance in the database, which might be outdated
        self.state_1.permissions.add(self.permission_1)
        self.state_2.permissions.add(self.permission_2)
        self.state_1.member_characters.add(self.main)
        user = User.objects.get(pk=self.user.pk)
        user.profile.state = self.state_2
        self.assertFalse(user.has_perm(PERMISSION_1))
        self.assertTrue(user.has_perm(PERMISSION_2))


class TestAuthenticate(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.main_character = EveCharacter.objects.create(
            character_id=1,
            character_name='Main Character',
            corporation_id=1,
            corporation_name='Corp',
            corporation_ticker='CORP',
        )
        cls.alt_character = EveCharacter.objects.create(
            character_id=2,
            character_name='Alt Character',
            corporation_id=1,
            corporation_name='Corp',
            corporation_ticker='CORP',
        )
        cls.unclaimed_character = EveCharacter.objects.create(
            character_id=3,
            character_name='Unclaimed Character',
            corporation_id=1,
            corporation_name='Corp',
            corporation_ticker='CORP',
        )
        cls.user = AuthUtils.create_user('test_user', disconnect_signals=True)
        cls.old_user = AuthUtils.create_user('old_user', disconnect_signals=True)
        AuthUtils.disconnect_signals()
        CharacterOwnership.objects.create(user=cls.user, character=cls.main_character, owner_hash='1')
        CharacterOwnership.objects.create(user=cls.user, character=cls.alt_character, owner_hash='2')
        UserProfile.objects.update_or_create(user=cls.user, defaults={'main_character': cls.main_character})
        AuthUtils.connect_signals()

    def test_authenticate_main_character(self):
        t = Token(character_id=self.main_character.character_id, character_owner_hash='1')
        user = StateBackend().authenticate(token=t)
        self.assertEqual(user, self.user)

    """ Alt Login disabled
    def test_authenticate_alt_character(self):
        t = Token(character_id=self.alt_character.character_id, character_owner_hash='2')
        user = StateBackend().authenticate(token=t)
        self.assertEqual(user, self.user)
    """

    def test_authenticate_alt_character_fail(self):
        t = Token(character_id=self.alt_character.character_id, character_owner_hash='2')
        user = StateBackend().authenticate(token=t)
        self.assertEqual(user, None)

    def test_authenticate_unclaimed_character(self):
        t = Token(character_id=self.unclaimed_character.character_id, character_name=self.unclaimed_character.character_name, character_owner_hash='3')
        user = StateBackend().authenticate(token=t)
        self.assertNotEqual(user, self.user)
        self.assertEqual(user.username, 'Unclaimed_Character')
        self.assertEqual(user.profile.main_character, self.unclaimed_character)

    """ Alt Login disabled
    def test_authenticate_character_record(self):
        t = Token(character_id=self.unclaimed_character.character_id, character_name=self.unclaimed_character.character_name, character_owner_hash='4')
        OwnershipRecord.objects.create(user=self.old_user, character=self.unclaimed_character, owner_hash='4')
        user = StateBackend().authenticate(token=t)
        self.assertEqual(user, self.old_user)
        self.assertTrue(CharacterOwnership.objects.filter(owner_hash='4', user=self.old_user).exists())
        self.assertTrue(user.profile.main_character)
    """

    def test_authenticate_character_record_fails(self):
        t = Token(character_id=self.unclaimed_character.character_id, character_name=self.unclaimed_character.character_name, character_owner_hash='4')
        OwnershipRecord.objects.create(user=self.old_user, character=self.unclaimed_character, owner_hash='4')
        user = StateBackend().authenticate(token=t)
        self.assertEqual(user, self.old_user)
        self.assertTrue(CharacterOwnership.objects.filter(owner_hash='4', user=self.old_user).exists())
        self.assertTrue(user.profile.main_character)

    def test_iterate_username(self):
        t = Token(character_id=self.unclaimed_character.character_id,
                    character_name=self.unclaimed_character.character_name, character_owner_hash='3')
        username = StateBackend().authenticate(token=t).username
        t.character_owner_hash = '4'
        username_1 = StateBackend().authenticate(token=t).username
        t.character_owner_hash = '5'
        username_2 = StateBackend().authenticate(token=t).username
        self.assertNotEqual(username, username_1, username_2)
        self.assertTrue(username_1.endswith('_1'))
        self.assertTrue(username_2.endswith('_2'))
