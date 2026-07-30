from unittest.mock import Mock, patch

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from esi.models import Token

from allianceauth.tests.auth_utils import AuthUtils

from ..evelinks import eveimageserver
from ..models import EveAllianceInfo, EveCharacter, EveCorporationInfo, EveFactionInfo
from ..providers import Alliance, Character, Corporation
from .esi_client_stub import EsiClientStub


class EveCharacterTestCase(TestCase):
    def test_corporation_prop(self):
        """
        Test that the correct corporation is returned by the corporation property
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=12345,
            alliance_name='character.alliance.name',
        )

        expected = EveCorporationInfo.objects.create(
            corporation_id=2345,
            corporation_name='corp.name',
            corporation_ticker='cc1',
            member_count=10,
            alliance=None,
        )

        incorrect = EveCorporationInfo.objects.create(
            corporation_id=9999,
            corporation_name='corp.name1',
            corporation_ticker='cc11',
            member_count=10,
            alliance=None,
        )

        self.assertEqual(character.corporation, expected)
        self.assertNotEqual(character.corporation, incorrect)

    def test_corporation_prop_exception(self):
        """
        Check that an exception is raised when the expected
        object is not in the database
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=123456,
            alliance_name='character.alliance.name',
        )

        with self.assertRaises(EveCorporationInfo.DoesNotExist):
            character.corporation

    def test_alliance_prop(self):
        """
        Test that the correct alliance is returned by the alliance property
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=3456,
            alliance_name='character.alliance.name',
        )

        expected = EveAllianceInfo.objects.create(
            alliance_id=3456,
            alliance_name='alliance.name',
            alliance_ticker='ac2',
            executor_corp_id=2345,
        )

        incorrect = EveAllianceInfo.objects.create(
            alliance_id=9001,
            alliance_name='alliance.name1',
            alliance_ticker='ac1',
            executor_corp_id=2654,
        )

        self.assertEqual(character.alliance, expected)
        self.assertNotEqual(character.alliance, incorrect)

    def test_alliance_prop_exception(self):
        """
        Check that an exception is raised when the expected
        object is not in the database
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=3456,
            alliance_name='character.alliance.name',
        )

        with self.assertRaises(EveAllianceInfo.DoesNotExist):
            character.alliance

    def test_alliance_prop_none(self):
        """
        Check that None is returned when the character has no alliance
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=None,
            alliance_name=None,
        )

        self.assertIsNone(character.alliance)

    def test_faction_prop(self):
        """
        Test that the correct faction is returned by the alliance property
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=3456,
            alliance_name='character.alliance.name',
            faction_id=1337,
            faction_name='character.faction.name'
        )

        expected = EveFactionInfo.objects.create(faction_id=1337, faction_name='faction.name')
        incorrect = EveFactionInfo.objects.create(faction_id=8008, faction_name='faction.badname')

        self.assertEqual(character.faction, expected)
        self.assertNotEqual(character.faction, incorrect)

    def test_faction_prop_exception(self):
        """
        Check that an exception is raised when the expected
        object is not in the database
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=3456,
            alliance_name='character.alliance.name',
            faction_id=1337,
            faction_name='character.faction.name'
        )

        with self.assertRaises(EveFactionInfo.DoesNotExist):
            character.faction

    def test_faction_prop_none(self):
        """
        Check that None is returned when the character has no alliance
        """
        character = EveCharacter.objects.create(
            character_id=1234,
            character_name='character.name',
            corporation_id=2345,
            corporation_name='character.corp.name',
            corporation_ticker='cc1',
            alliance_id=None,
            alliance_name=None,
            faction_id=None,
            faction_name=None,
        )

        self.assertIsNone(character.faction)

    @patch('allianceauth.eveonline.providers.provider')
    def test_update_character(self, mock_provider):
        mock_provider.get_corp.return_value = Corporation(
            id=2002,
            name='Dummy Corp 2',
            ticker='DC2',
            ceo_id=1001,
            members=34,
        )

        my_character = EveCharacter.objects.create(
            character_id=1001,
            character_name='Bruce Wayne',
            corporation_id=2001,
            corporation_name='Dummy Corp 1',
            corporation_ticker='DC1',
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            faction_id=1337,
            faction_name='Dummy Faction 1',
        )
        my_updated_character = Character(
            name='Bruce X. Wayne',
            corp_id=2002,
            faction_id=None,
        )
        my_character.update_character(my_updated_character)
        self.assertEqual(my_character.character_name, 'Bruce X. Wayne')
        self.assertFalse(my_character.faction_id)

        # todo: add test cases not yet covered, e.g. with alliance

    def test_image_url(self):
        self.assertEqual(
            EveCharacter.generic_portrait_url(42),
            eveimageserver._eve_entity_image_url('character', 42)
        )
        self.assertEqual(
            EveCharacter.generic_portrait_url(42, 256),
            eveimageserver._eve_entity_image_url('character', 42, 256)
        )

    def test_portrait_urls(self):
        x = EveCharacter(
            character_id=42,
            character_name='character.name',
            corporation_id=123,
            corporation_name='corporation.name',
            corporation_ticker='ABC',
        )
        self.assertEqual(
            x.portrait_url(),
            eveimageserver._eve_entity_image_url('character', 42)
        )
        self.assertEqual(
            x.portrait_url(64),
            eveimageserver._eve_entity_image_url('character', 42, size=64)
        )
        self.assertEqual(
            x.portrait_url_32,
            eveimageserver._eve_entity_image_url('character', 42, size=32)
        )
        self.assertEqual(
            x.portrait_url_64,
            eveimageserver._eve_entity_image_url('character', 42, size=64)
        )
        self.assertEqual(
            x.portrait_url_128,
            eveimageserver._eve_entity_image_url('character', 42, size=128)
        )
        self.assertEqual(
            x.portrait_url_256,
            eveimageserver._eve_entity_image_url('character', 42, size=256)
        )

    def test_corporation_logo_urls(self):
        x = EveCharacter(
            character_id=42,
            character_name='character.name',
            corporation_id=123,
            corporation_name='corporation.name',
            corporation_ticker='ABC',
        )
        self.assertEqual(
            x.corporation_logo_url(),
            eveimageserver._eve_entity_image_url('corporation', 123)
        )
        self.assertEqual(
            x.corporation_logo_url(256),
            eveimageserver._eve_entity_image_url('corporation', 123, size=256)
        )
        self.assertEqual(
            x.corporation_logo_url_32,
            eveimageserver._eve_entity_image_url('corporation', 123, size=32)
        )
        self.assertEqual(
            x.corporation_logo_url_64,
            eveimageserver._eve_entity_image_url('corporation', 123, size=64)
        )
        self.assertEqual(
            x.corporation_logo_url_128,
            eveimageserver._eve_entity_image_url('corporation', 123, size=128)
        )
        self.assertEqual(
            x.corporation_logo_url_256,
            eveimageserver._eve_entity_image_url('corporation', 123, size=256)
        )

    def test_alliance_logo_urls(self):
        x = EveCharacter(
            character_id=42,
            character_name='character.name',
            corporation_id=123,
            corporation_name='corporation.name',
            corporation_ticker='ABC',
        )
        self.assertEqual(
            x.alliance_logo_url(),
            ''
        )
        self.assertEqual(
            x.alliance_logo_url_32,
            ''
        )
        self.assertEqual(
            x.alliance_logo_url_64,
            ''
        )
        self.assertEqual(
            x.alliance_logo_url_128,
            ''
        )
        self.assertEqual(
            x.alliance_logo_url_256,
            ''
        )
        x.alliance_id = 987
        self.assertEqual(
            x.alliance_logo_url(),
            eveimageserver._eve_entity_image_url('alliance', 987)
        )
        self.assertEqual(
            x.alliance_logo_url(128),
            eveimageserver._eve_entity_image_url('alliance', 987, size=128)
        )
        self.assertEqual(
            x.alliance_logo_url_32,
            eveimageserver._eve_entity_image_url('alliance', 987, size=32)
        )
        self.assertEqual(
            x.alliance_logo_url_64,
            eveimageserver._eve_entity_image_url('alliance', 987, size=64)
        )
        self.assertEqual(
            x.alliance_logo_url_128,
            eveimageserver._eve_entity_image_url('alliance', 987, size=128)
        )
        self.assertEqual(
            x.alliance_logo_url_256,
            eveimageserver._eve_entity_image_url('alliance', 987, size=256)
        )


class EveAllianceTestCase(TestCase):

    def test_str(self):
        my_alliance = EveAllianceInfo(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        self.assertEqual(str(my_alliance), 'Dummy Alliance 1')

    @patch(
        'allianceauth.eveonline.models.EveCorporationInfo.objects.create_corporation'
    )
    def test_populate_alliance(self, mock_create_corporation):

        def create_corp(corp_id):
            if corp_id == 2002:
                EveCorporationInfo.objects.create(
                    corporation_id=2002,
                    corporation_name='Dummy Corporation 2',
                    corporation_ticker='DC2',
                    member_count=87,
                )
            else:
                raise ValueError()

        mock_EveAllianceProviderManager = Mock()
        mock_EveAllianceProviderManager.get_alliance.return_value = \
            Alliance(
                id=3001,
                name='Dummy Alliance 1',
                corp_ids=[2001, 2002]
            )
        mock_create_corporation.side_effect = create_corp

        EveCorporationInfo.objects.create(
            corporation_id=2001,
            corporation_name='Dummy Corporation 1',
            corporation_ticker='DC1',
            member_count=42,
        )

        my_alliance = EveAllianceInfo(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        my_alliance.provider = mock_EveAllianceProviderManager
        my_alliance.save()
        my_alliance.populate_alliance()

        for corporation in (
            EveCorporationInfo.objects.filter(corporation_id__in=[2001, 2002])
        ):
            self.assertEqual(corporation.alliance, my_alliance)

    def test_update_alliance_with_object(self):
        my_alliance = EveAllianceInfo.objects.create(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        updated_alliance = Alliance(
            id=3002,
            name='Dummy Alliance 2',
            corp_ids=[2004],
            executor_corp_id=2004
        )
        my_alliance.update_alliance(updated_alliance)
        my_alliance.refresh_from_db()
        self.assertEqual(int(my_alliance.executor_corp_id), 2004)

        # potential bug
        # update_alliance() is only updateting executor_corp_id when object is given

    def test_update_alliance_wo_object(self):
        mock_EveAllianceProviderManager = Mock()
        mock_EveAllianceProviderManager.get_alliance.return_value = \
            Alliance(
                id=3002,
                name='Dummy Alliance 2',
                corp_ids=[2004],
                executor_corp_id=2004
            )

        my_alliance = EveAllianceInfo.objects.create(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        my_alliance.provider = mock_EveAllianceProviderManager
        my_alliance.save()
        Alliance(
            name='Dummy Alliance 2',
            corp_ids=[2004],
            executor_corp_id=2004
        )
        my_alliance.update_alliance()
        my_alliance.refresh_from_db()
        self.assertEqual(int(my_alliance.executor_corp_id), 2004)

        # potential bug
        # update_alliance() is only updateting executor_corp_id nothing else ???

    def test_image_url(self):
        self.assertEqual(
            EveAllianceInfo.generic_logo_url(42),
            eveimageserver._eve_entity_image_url('alliance', 42)
        )
        self.assertEqual(
            EveAllianceInfo.generic_logo_url(42, 256),
            eveimageserver._eve_entity_image_url('alliance', 42, 256)
        )

    def test_logo_url(self):
        x = EveAllianceInfo(
            alliance_id=42,
            alliance_name='alliance.name',
            alliance_ticker='ABC',
            executor_corp_id=123
        )
        self.assertEqual(
            x.logo_url(),
            'https://images.evetech.net/alliances/42/logo?size=32'
        )
        self.assertEqual(
            x.logo_url(64),
            'https://images.evetech.net/alliances/42/logo?size=64'
        )
        self.assertEqual(
            x.logo_url_32,
            'https://images.evetech.net/alliances/42/logo?size=32'
        )
        self.assertEqual(
            x.logo_url_64,
            'https://images.evetech.net/alliances/42/logo?size=64'
        )
        self.assertEqual(
            x.logo_url_128,
            'https://images.evetech.net/alliances/42/logo?size=128'
        )
        self.assertEqual(
            x.logo_url_256,
            'https://images.evetech.net/alliances/42/logo?size=256'
        )


class EveCorporationTestCase(TestCase):

    def setUp(self):
        my_alliance = EveAllianceInfo.objects.create(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        self.my_corp = EveCorporationInfo(
            corporation_id=2001,
            corporation_name='Dummy Corporation 1',
            corporation_ticker='DC1',
            member_count=42,
            alliance=my_alliance
        )

    def test_str(self):
        self.assertEqual(str(self.my_corp), 'Dummy Corporation 1')

    def test_update_corporation_from_object_w_alliance(self):
        updated_corp = Corporation(
            members=87
        )
        self.my_corp.update_corporation(updated_corp)
        self.assertEqual(self.my_corp.member_count, 87)

        # potential bug
        # update_corporation updates member_count only

    def test_update_corporation_no_object_w_alliance(self):
        mock_provider = Mock()
        mock_provider.get_corporation.return_value = Corporation(members=87)
        self.my_corp.provider = mock_provider

        self.my_corp.update_corporation()
        self.assertEqual(self.my_corp.member_count, 87)

    def test_update_corporation_from_object_wo_alliance(self):
        my_corp2 = EveCorporationInfo(
            corporation_id=2011,
            corporation_name='Dummy Corporation 11',
            corporation_ticker='DC11',
            member_count=6
        )
        updated_corp = Corporation(
            members=8
        )
        my_corp2.update_corporation(updated_corp)
        self.assertEqual(my_corp2.member_count, 8)
        self.assertIsNone(my_corp2.alliance)

    def test_image_url(self):
        self.assertEqual(
            EveCorporationInfo.generic_logo_url(42),
            eveimageserver._eve_entity_image_url('corporation', 42)
        )
        self.assertEqual(
            EveCorporationInfo.generic_logo_url(42, 256),
            eveimageserver._eve_entity_image_url('corporation', 42, 256)
        )

    def test_logo_url(self):
        self.assertEqual(
            self.my_corp.logo_url(),
            'https://images.evetech.net/corporations/2001/logo?size=32'
        )
        self.assertEqual(
            self.my_corp.logo_url(64),
            'https://images.evetech.net/corporations/2001/logo?size=64'
        )
        self.assertEqual(
            self.my_corp.logo_url_32,
            'https://images.evetech.net/corporations/2001/logo?size=32'
        )
        self.assertEqual(
            self.my_corp.logo_url_64,
            'https://images.evetech.net/corporations/2001/logo?size=64'
        )
        self.assertEqual(
            self.my_corp.logo_url_128,
            'https://images.evetech.net/corporations/2001/logo?size=128'
        )
        self.assertEqual(
            self.my_corp.logo_url_256,
            'https://images.evetech.net/corporations/2001/logo?size=256'
        )


@patch('allianceauth.eveonline.providers.esi_client_factory')
@patch("allianceauth.eveonline.models.notify")
class TestCharacterUpdate(TestCase):
    def test_should_update_normal_character(self, mock_notify, mock_esi_client_factory):
        # given
        mock_esi_client_factory.return_value = EsiClientStub()
        my_character = EveCharacter.objects.create(
            character_id=1001,
            character_name="not my name",
            corporation_id=2002,
            corporation_name="Wayne Food",
            corporation_ticker="WYF",
            alliance_id=None
        )
        # when
        my_character.update_character()
        # then
        my_character.refresh_from_db()
        self.assertEqual(my_character.character_name, "Bruce Wayne")
        self.assertEqual(my_character.corporation_id, 2001)
        self.assertEqual(my_character.corporation_name, "Wayne Technologies")
        self.assertEqual(my_character.corporation_ticker, "WTE")
        self.assertEqual(my_character.alliance_id, 3001)
        self.assertEqual(my_character.alliance_name, "Wayne Enterprises")
        self.assertEqual(my_character.alliance_ticker, "WYE")
        self.assertFalse(mock_notify.called)

    def test_should_update_dead_character_with_owner(
        self, mock_notify, mock_esi_client_factory
    ):
        # given
        mock_esi_client_factory.return_value = EsiClientStub()
        character_1666 = EveCharacter.objects.create(
            character_id=1666,
            character_name="Hal Jordan",
            corporation_id=2002,
            corporation_name="Wayne Food",
            corporation_ticker="WYF",
            alliance_id=None
        )
        user = AuthUtils.create_user("Bruce Wayne")
        token_1666 = Token.objects.create(
            user=user,
            character_id=character_1666.character_id,
            character_name=character_1666.character_name,
            character_owner_hash="ABC123-1666",
        )
        character_1001 = EveCharacter.objects.create(
            character_id=1001,
            character_name="Bruce Wayne",
            corporation_id=2001,
            corporation_name="Wayne Technologies",
            corporation_ticker="WYT",
            alliance_id=None
        )
        token_1001 = Token.objects.create(
            user=user,
            character_id=character_1001.character_id,
            character_name=character_1001.character_name,
            character_owner_hash="ABC123-1001",
        )
        # when
        character_1666.update_character()
        # then
        character_1666.refresh_from_db()
        self.assertTrue(character_1666.is_biomassed)
        self.assertNotIn(token_1666, user.token_set.all())
        self.assertIn(token_1001, user.token_set.all())
        with self.assertRaises(ObjectDoesNotExist):
            self.assertTrue(character_1666.character_ownership)
        user.profile.refresh_from_db()
        self.assertIsNone(user.profile.main_character)
        self.assertTrue(mock_notify.called)

    def test_should_handle_dead_character_without_owner(
        self, mock_notify, mock_esi_client_factory
    ):
        # given
        mock_esi_client_factory.return_value = EsiClientStub()
        character_1666 = EveCharacter.objects.create(
            character_id=1666,
            character_name="Hal Jordan",
            corporation_id=1011,
            corporation_name="LexCorp",
            corporation_ticker='LC',
            alliance_id=None
        )
        # when
        character_1666.update_character()
        # then
        character_1666.refresh_from_db()
        self.assertTrue(character_1666.is_biomassed)
        self.assertFalse(mock_notify.called)
