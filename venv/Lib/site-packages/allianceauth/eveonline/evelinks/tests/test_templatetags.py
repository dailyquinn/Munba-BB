from django.test import TestCase

from ...models import EveCharacter, EveCorporationInfo, EveAllianceInfo
from .. import eveimageserver, evewho, dotlan, zkillboard
from ...templatetags import evelinks


class TestTemplateTags(TestCase):

    def setUp(self):
        self.my_character = EveCharacter.objects.create(
            character_id=1001,
            character_name='Bruce Wayne',
            corporation_id=2001,
            corporation_name='Dummy Corporation 1',
            corporation_ticker='DC1',
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
        )
        self.my_character_2 = EveCharacter.objects.create(
            character_id=1002,
            character_name='Peter Parker',
            corporation_id=2002,
            corporation_name='Dummy Corporation 2',
            corporation_ticker='DC2',
        )
        self.my_alliance = EveAllianceInfo.objects.create(
            alliance_id=3001,
            alliance_name='Dummy Alliance 1',
            alliance_ticker='DA1',
            executor_corp_id=2001
        )
        self.my_corporation = EveCorporationInfo(
            corporation_id=2001,
            corporation_name='Dummy Corporation 1',
            corporation_ticker='DC1',
            member_count=42,
            alliance=self.my_alliance
        )

        self.my_region_id = 8001
        self.my_region_name = 'Southpark'

        self.my_solar_system_id = 9001
        self.my_solar_system_name = 'Gotham'


    def test_evewho_character_url(self):
        self.assertEqual(
            evelinks.evewho_character_url(self.my_character),
            evewho.character_url(self.my_character.character_id),
        )
        self.assertEqual(
            evelinks.evewho_character_url(None),
            ''
        )
        self.assertEqual(
            evelinks.evewho_character_url(self.my_character.character_id),
            evewho.character_url(self.my_character.character_id),
        )


    def test_evewho_corporation_url(self):
        self.assertEqual(
            evelinks.evewho_corporation_url(self.my_character),
            evewho.corporation_url(self.my_character.corporation_id),
        )
        self.assertEqual(
            evelinks.evewho_corporation_url(self.my_corporation),
            evewho.corporation_url(self.my_corporation.corporation_id),
        )
        self.assertEqual(
            evelinks.evewho_corporation_url(None),
            ''
        )
        self.assertEqual(
            evelinks.evewho_corporation_url(self.my_character.corporation_id),
            evewho.corporation_url(self.my_character.corporation_id),
        )


    def test_evewho_alliance_url(self):
        self.assertEqual(
            evelinks.evewho_alliance_url(self.my_character),
            evewho.alliance_url(self.my_character.alliance_id),
        )
        self.assertEqual(
            evelinks.evewho_alliance_url(self.my_character_2),
            '',
        )
        self.assertEqual(
            evelinks.evewho_alliance_url(self.my_alliance),
            evewho.alliance_url(self.my_alliance.alliance_id),
        )
        self.assertEqual(
            evelinks.evewho_alliance_url(None),
            ''
        )
        self.assertEqual(
            evelinks.evewho_alliance_url(self.my_character.alliance_id),
            evewho.alliance_url(self.my_character.alliance_id),
        )


    # dotlan

    def test_dotlan_corporation_url(self):
        self.assertEqual(
            evelinks.dotlan_corporation_url(self.my_character),
            dotlan.corporation_url(self.my_character.corporation_name),
        )
        self.assertEqual(
            evelinks.dotlan_corporation_url(self.my_corporation),
            dotlan.corporation_url(self.my_corporation.corporation_name),
        )
        self.assertEqual(
            evelinks.dotlan_corporation_url(None),
            ''
        )
        self.assertEqual(
            evelinks.dotlan_corporation_url(self.my_character.corporation_name),
            dotlan.corporation_url(self.my_character.corporation_name),
        )


    def test_dotlan_alliance_url(self):
        self.assertEqual(
            evelinks.dotlan_alliance_url(self.my_character),
            dotlan.alliance_url(self.my_character.alliance_name),
        )
        self.assertEqual(
            evelinks.dotlan_alliance_url(self.my_character_2),
            '',
        )
        self.assertEqual(
            evelinks.dotlan_alliance_url(self.my_alliance),
            dotlan.alliance_url(self.my_alliance.alliance_name),
        )
        self.assertEqual(
            evelinks.dotlan_alliance_url(None),
            ''
        )
        self.assertEqual(
            evelinks.dotlan_alliance_url(self.my_character.alliance_name),
            dotlan.alliance_url(self.my_character.alliance_name),
        )

    def test_dotlan_region_url(self):
        self.assertEqual(
            evelinks.dotlan_region_url(self.my_region_name),
            dotlan.region_url(self.my_region_name),
        )
        self.assertEqual(
            evelinks.dotlan_region_url(None),
            ''
        )

    def test_dotlan_solar_system_url(self):
        self.assertEqual(
            evelinks.dotlan_solar_system_url(self.my_solar_system_name),
            dotlan.solar_system_url(self.my_solar_system_name),
        )
        self.assertEqual(
            evelinks.dotlan_solar_system_url(None),
            ''
        )


    # zkillboard

    def test_zkillboard_character_url(self):
        self.assertEqual(
            evelinks.zkillboard_character_url(self.my_character),
            zkillboard.character_url(self.my_character.character_id),
        )
        self.assertEqual(
            evelinks.zkillboard_character_url(None),
            ''
        )
        self.assertEqual(
            evelinks.zkillboard_character_url(self.my_character.character_id),
            zkillboard.character_url(self.my_character.character_id),
        )


    def test_zkillboard_corporation_url(self):
        self.assertEqual(
            evelinks.zkillboard_corporation_url(self.my_character),
            zkillboard.corporation_url(self.my_character.corporation_id),
        )
        self.assertEqual(
            evelinks.zkillboard_corporation_url(self.my_corporation),
            zkillboard.corporation_url(self.my_corporation.corporation_id),
        )
        self.assertEqual(
            evelinks.zkillboard_corporation_url(None),
            ''
        )
        self.assertEqual(
            evelinks.zkillboard_corporation_url(self.my_character.corporation_id),
            zkillboard.corporation_url(self.my_character.corporation_id),
        )


    def test_zkillboard_alliance_url(self):
        self.assertEqual(
            evelinks.zkillboard_alliance_url(self.my_character),
            zkillboard.alliance_url(self.my_character.alliance_id),
        )
        self.assertEqual(
            evelinks.zkillboard_alliance_url(self.my_character_2),
            '',
        )
        self.assertEqual(
            evelinks.zkillboard_alliance_url(self.my_alliance),
            zkillboard.alliance_url(self.my_alliance.alliance_id),
        )
        self.assertEqual(
            evelinks.zkillboard_alliance_url(None),
            ''
        )
        self.assertEqual(
            evelinks.zkillboard_alliance_url(self.my_character.alliance_id),
            zkillboard.alliance_url(self.my_character.alliance_id),
        )


    def test_zkillboard_region_url(self):
        self.assertEqual(
            evelinks.zkillboard_region_url(self.my_region_id),
            zkillboard.region_url(self.my_region_id),
        )
        self.assertEqual(
            evelinks.zkillboard_region_url(None),
            ''
        )


    def test_zkillboard_solar_system_url(self):
        self.assertEqual(
            evelinks.zkillboard_solar_system_url(self.my_solar_system_id),
            zkillboard.solar_system_url(self.my_solar_system_id),
        )
        self.assertEqual(
            evelinks.zkillboard_solar_system_url(None),
            ''
        )


    # image URLs

    def test_character_portrait_url(self):
        self.assertEqual(
            evelinks.character_portrait_url(123),
            EveCharacter.generic_portrait_url(123)

        ),
        self.assertEqual(
            evelinks.character_portrait_url(123, 128),
            EveCharacter.generic_portrait_url(123, 128)

        )
        self.assertEqual(
            evelinks.character_portrait_url(123, 99),
            ''
        )
        self.assertEqual(
            evelinks.character_portrait_url(self.my_character),
            self.my_character.portrait_url()
        )
        self.assertEqual(
            evelinks.character_portrait_url(None),
            ''
        )


    def test_corporation_logo_url(self):
        self.assertEqual(
            evelinks.corporation_logo_url(123),
            EveCorporationInfo.generic_logo_url(123)
        ),
        self.assertEqual(
            evelinks.corporation_logo_url(123, 128),
            EveCorporationInfo.generic_logo_url(123, 128)
        )
        self.assertEqual(
            evelinks.corporation_logo_url(123, 99),
            ''
        )
        self.assertEqual(
            evelinks.corporation_logo_url(self.my_corporation),
            self.my_corporation.logo_url()
        )
        self.assertEqual(
            evelinks.corporation_logo_url(self.my_character),
            self.my_character.corporation_logo_url()
        )
        self.assertEqual(
            evelinks.corporation_logo_url(None),
            ''
        )


    def test_alliance_logo_url(self):
        self.assertEqual(
            evelinks.alliance_logo_url(123),
            EveAllianceInfo.generic_logo_url(123)
        ),
        self.assertEqual(
            evelinks.alliance_logo_url(123, 128),
            EveAllianceInfo.generic_logo_url(123, 128)
        )
        self.assertEqual(
            evelinks.alliance_logo_url(123, 99),
            ''
        )
        self.assertEqual(
            evelinks.alliance_logo_url(self.my_alliance),
            self.my_alliance.logo_url()
        )
        self.assertEqual(
            evelinks.alliance_logo_url(self.my_character),
            self.my_character.alliance_logo_url()
        )
        self.assertEqual(
            evelinks.alliance_logo_url(None),
            ''
        )
        self.assertEqual(
            evelinks.alliance_logo_url(self.my_character_2),
            ''
        )

    def test_type_icon_url(self):
        expected = eveimageserver.type_icon_url(123)
        self.assertEqual(evelinks.type_icon_url(123), expected)

        expected = eveimageserver.type_icon_url(123, 128)
        self.assertEqual(evelinks.type_icon_url(123, 128), expected)

        expected = ''
        self.assertEqual(evelinks.type_icon_url(123, 99), expected)

        expected = ''
        self.assertEqual(evelinks.type_icon_url(None), expected)

    def test_type_render_url(self):
        expected = eveimageserver.type_render_url(123)
        self.assertEqual(evelinks.type_render_url(123), expected)

        expected = eveimageserver.type_render_url(123, 128)
        self.assertEqual(evelinks.type_render_url(123, 128), expected)

        expected = ''
        self.assertEqual(evelinks.type_render_url(123, 99), expected)

        expected = ''
        self.assertEqual(evelinks.type_render_url(None), expected)
