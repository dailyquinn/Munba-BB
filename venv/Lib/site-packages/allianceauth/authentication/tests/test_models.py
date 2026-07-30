from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo,\
    EveAllianceInfo, EveFactionInfo
from allianceauth.tests.auth_utils import AuthUtils
from esi.errors import IncompleteResponseError
from esi.models import Token

from ..models import CharacterOwnership, State, get_guest_state
from ..tasks import check_character_ownership

MODULE_PATH = 'allianceauth.authentication'


class CharacterOwnershipTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('user', disconnect_signals=True)
        cls.alt_user = AuthUtils.create_user('alt_user', disconnect_signals=True)
        cls.character = EveCharacter.objects.create(
            character_id=1,
            character_name='Main Character',
            corporation_id=1,
            corporation_name='Corp',
            corporation_ticker='CORP',
        )

    def test_create_ownership(self):
        Token.objects.create(
            user=self.user,
            character_id=self.character.character_id,
            character_name=self.character.character_name,
            character_owner_hash='1',
        )
        co = CharacterOwnership.objects.get(character=self.character)
        self.assertEqual(co.user, self.user)
        self.assertEqual(co.owner_hash, '1')

    def test_transfer_ownership(self):
        Token.objects.create(
            user=self.user,
            character_id=self.character.character_id,
            character_name=self.character.character_name,
            character_owner_hash='1',
        )
        Token.objects.create(
            user=self.alt_user,
            character_id=self.character.character_id,
            character_name=self.character.character_name,
            character_owner_hash='2',
        )
        co = CharacterOwnership.objects.get(character=self.character)
        self.assertNotEqual(self.user, co.user)
        self.assertEqual(self.alt_user, co.user)

    def test_clear_main_character(self):
        Token.objects.create(
            user=self.user,
            character_id=self.character.character_id,
            character_name=self.character.character_name,
            character_owner_hash='1',
        )
        self.user.profile.main_character = self.character
        self.user.profile.save()
        Token.objects.create(
            user=self.alt_user,
            character_id=self.character.character_id,
            character_name=self.character.character_name,
            character_owner_hash='2',
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.assertIsNone(self.user.profile.main_character)


class StateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('test_user', disconnect_signals=True)
        AuthUtils.add_main_character(cls.user, 'Test Character', '1', corp_id='1', alliance_id='1',
                                    corp_name='Test Corp', alliance_name='Test Alliance', faction_id=1337,
                                    faction_name='Permabanned')
        cls.guest_state = get_guest_state()
        cls.test_character = EveCharacter.objects.get(character_id='1')
        cls.test_corporation = EveCorporationInfo.objects.create(corporation_id='1', corporation_name='Test Corp',
                                                                corporation_ticker='TEST', member_count=1)
        cls.test_alliance = EveAllianceInfo.objects.create(alliance_id='1', alliance_name='Test Alliance',
                                                            alliance_ticker='TEST', executor_corp_id='1')
        cls.test_faction = EveFactionInfo.objects.create(faction_id=1337, faction_name='Permabanned')
        cls.member_state = State.objects.create(
            name='Test Member',
            priority=150,
        )

    def _refresh_user(self):
        self.user = User.objects.get(pk=self.user.pk)

    def test_state_assignment_on_character_change(self):
        self.member_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.member_state)

        self.member_state.member_characters.remove(self.test_character)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)

    def test_state_assignment_on_corporation_change(self):
        self.member_state.member_corporations.add(self.test_corporation)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.member_state)

        self.member_state.member_corporations.remove(self.test_corporation)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)

    def test_state_assignment_on_alliance_addition(self):
        self.member_state.member_alliances.add(self.test_alliance)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.member_state)

        self.member_state.member_alliances.remove(self.test_alliance)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)

    def test_state_assignment_on_faction_change(self):
        self.member_state.member_factions.add(self.test_faction)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.member_state)

        self.member_state.member_factions.remove(self.test_faction)
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)

    def test_state_assignment_on_higher_priority_state_creation(self):
        self.member_state.member_characters.add(self.test_character)
        higher_state = State.objects.create(
            name='Higher State',
            priority=200,
        )
        higher_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(higher_state, self.user.profile.state)
        higher_state.member_characters.clear()
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        self.member_state.member_characters.clear()

    def test_state_assignment_on_lower_priority_state_creation(self):
        self.member_state.member_characters.add(self.test_character)
        lower_state = State.objects.create(
            name='Lower State',
            priority=125,
        )
        lower_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        lower_state.member_characters.clear()
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        self.member_state.member_characters.clear()

    def test_state_assignment_on_priority_change(self):
        self.member_state.member_characters.add(self.test_character)
        lower_state = State.objects.create(
            name='Lower State',
            priority=125,
        )
        lower_state.member_characters.add(self.test_character)
        self._refresh_user()
        lower_state.priority = 500
        lower_state.save()
        self._refresh_user()
        self.assertEqual(lower_state, self.user.profile.state)
        lower_state.priority = 125
        lower_state.save()
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)

    def test_state_assignment_on_state_deletion(self):
        self.member_state.member_characters.add(self.test_character)
        higher_state = State.objects.create(
            name='Higher State',
            priority=200,
        )
        higher_state.member_characters.add(self.test_character)
        self._refresh_user()
        self.assertEqual(higher_state, self.user.profile.state)
        higher_state.delete()
        self.assertFalse(State.objects.filter(name='Higher State').count())
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)

    def test_state_assignment_on_public_toggle(self):
        self.member_state.member_characters.add(self.test_character)
        higher_state = State.objects.create(
            name='Higher State',
            priority=200,
        )
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)
        higher_state.public = True
        higher_state.save()
        self._refresh_user()
        self.assertEqual(higher_state, self.user.profile.state)
        higher_state.public = False
        higher_state.save()
        self._refresh_user()
        self.assertEqual(self.member_state, self.user.profile.state)

    def test_state_assignment_on_active_changed(self):
        self.member_state.member_characters.add(self.test_character)
        self.user.is_active = False
        self.user.save()
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)
        self.user.is_active = True
        self.user.save()
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.member_state)


class CharacterOwnershipCheckTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('test_user', disconnect_signals=True)
        AuthUtils.add_main_character(cls.user, 'Test Character', '1', corp_id='1', alliance_id='1',
                                        corp_name='Test Corp', alliance_name='Test Alliance')
        cls.character = EveCharacter.objects.get(character_id=1)
        cls.token = Token.objects.create(
            user=cls.user,
            character_id=1,
            character_name='Test',
            character_owner_hash='1',
        )
        cls.ownership = CharacterOwnership.objects.get(character=cls.character)

    @mock.patch(MODULE_PATH + '.tasks.Token.update_token_data')
    def test_no_change_owner_hash(self, update_token_data):
        # makes sure the ownership isn't delete if owner hash hasn't changed
        check_character_ownership(self.ownership)
        self.assertTrue(CharacterOwnership.objects.filter(user=self.user).filter(character=self.character).exists())

    @mock.patch(MODULE_PATH + '.tasks.Token.update_token_data')
    def test_unable_to_update_token_data(self, update_token_data):
        # makes sure ownerships and tokens aren't hellpurged when there's problems with the SSO servers
        update_token_data.side_effect = IncompleteResponseError()
        check_character_ownership(self.ownership)
        self.assertTrue(CharacterOwnership.objects.filter(user=self.user).filter(character=self.character).exists())

        update_token_data.side_effect = KeyError()
        check_character_ownership(self.ownership)
        self.assertTrue(CharacterOwnership.objects.filter(user=self.user).filter(character=self.character).exists())

    @mock.patch(MODULE_PATH + '.tasks.Token.update_token_data')
    @mock.patch(MODULE_PATH + '.tasks.Token.delete')
    @mock.patch(MODULE_PATH + '.tasks.Token.objects.exists')
    @mock.patch(MODULE_PATH + '.tasks.CharacterOwnership.objects.filter')
    def test_owner_hash_changed(self, filter, exists, delete, update_token_data):
        # makes sure the ownership is revoked when owner hash changes
        filter.return_value.exists.return_value = False
        check_character_ownership(self.ownership)
        self.assertTrue(filter.return_value.delete.called)
