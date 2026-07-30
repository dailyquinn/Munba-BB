from django.test import TestCase

from ...models import EveCharacter, EveCorporationInfo, EveAllianceInfo
from .. import dotlan, zkillboard, evewho, eveimageserver
from ...templatetags import evelinks


class TestEveWho(TestCase):

    def test_alliance_url(self):
        self.assertEqual(
            evewho.alliance_url(12345678),
            'https://evewho.com/alliance/12345678'
        )

    def test_corporation_url(self):
        self.assertEqual(
            evewho.corporation_url(12345678),
            'https://evewho.com/corporation/12345678'
        )

    def test_character_url(self):
        self.assertEqual(
            evewho.character_url(12345678),
            'https://evewho.com/character/12345678'
        )


class TestDotlan(TestCase):

    def test_alliance_url(self):
        self.assertEqual(
            dotlan.alliance_url('Wayne Enterprices'),
            'https://evemaps.dotlan.net/alliance/Wayne_Enterprices'
        )

    def test_corporation_url(self):
        self.assertEqual(
            dotlan.corporation_url('Wayne Technology'),
            'https://evemaps.dotlan.net/corp/Wayne_Technology'
        )
        self.assertEqual(
            dotlan.corporation_url('Crédit Agricole'),
            'https://evemaps.dotlan.net/corp/Cr%C3%A9dit_Agricole'
        )

    def test_region_url(self):
        self.assertEqual(
            dotlan.region_url('Black Rise'),
            'https://evemaps.dotlan.net/map/Black_Rise'
        )

    def test_solar_system_url(self):
        self.assertEqual(
            dotlan.solar_system_url('Jita'),
            'https://evemaps.dotlan.net/system/Jita'
        )


class TestZkillboard(TestCase):

    def test_alliance_url(self):
        self.assertEqual(
            zkillboard.alliance_url(12345678),
            'https://zkillboard.com/alliance/12345678/'
        )

    def test_corporation_url(self):
        self.assertEqual(
            zkillboard.corporation_url(12345678),
            'https://zkillboard.com/corporation/12345678/'
        )

    def test_character_url(self):
        self.assertEqual(
            zkillboard.character_url(12345678),
            'https://zkillboard.com/character/12345678/'
        )


    def test_region_url(self):
        self.assertEqual(
            zkillboard.region_url(12345678),
            'https://zkillboard.com/region/12345678/'
        )

    def test_solar_system_url(self):
        self.assertEqual(
            zkillboard.solar_system_url(12345678),
            'https://zkillboard.com/system/12345678/'
        )


class TestEveImageServer(TestCase):
    """unit test for eveimageserver"""

    def test_sizes(self):
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42),
            'https://images.evetech.net/characters/42/portrait?size=32'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=32),
            'https://images.evetech.net/characters/42/portrait?size=32'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=64),
            'https://images.evetech.net/characters/42/portrait?size=64'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=128),
            'https://images.evetech.net/characters/42/portrait?size=128'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=256),
            'https://images.evetech.net/characters/42/portrait?size=256'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=512),
            'https://images.evetech.net/characters/42/portrait?size=512'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, size=1024),
            'https://images.evetech.net/characters/42/portrait?size=1024'
        )
        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('corporation', 42, size=-5)

        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('corporation', 42, size=0)

        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('corporation', 42, size=31)

        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('corporation', 42, size=1025)

        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('corporation', 42, size=2048)


    def test_variant(self):
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, variant='portrait'),
            'https://images.evetech.net/characters/42/portrait?size=32'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('alliance', 42, variant='logo'),
            'https://images.evetech.net/alliances/42/logo?size=32'
        )
        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('character', 42, variant='logo')


    def test_alliance(self):
        self.assertEqual(
            eveimageserver._eve_entity_image_url('alliance', 42),
            'https://images.evetech.net/alliances/42/logo?size=32'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('corporation', 42),
            'https://images.evetech.net/corporations/42/logo?size=32'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42),
            'https://images.evetech.net/characters/42/portrait?size=32'
        )
        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('station', 42)


    def test_tenants(self):
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, tenant='tranquility'),
            'https://images.evetech.net/characters/42/portrait?size=32&tenant=tranquility'
        )
        self.assertEqual(
            eveimageserver._eve_entity_image_url('character', 42, tenant='singularity'),
            'https://images.evetech.net/characters/42/portrait?size=32&tenant=singularity'
        )
        with self.assertRaises(ValueError):
            eveimageserver._eve_entity_image_url('character', 42, tenant='xxx')

    def test_alliance_logo_url(self):
        expected = 'https://images.evetech.net/alliances/42/logo?size=128'
        self.assertEqual(eveimageserver.alliance_logo_url(42, 128), expected)

    def test_corporation_logo_url(self):
        expected = 'https://images.evetech.net/corporations/42/logo?size=128'
        self.assertEqual(eveimageserver.corporation_logo_url(42, 128), expected)

    def test_character_portrait_url(self):
        expected = 'https://images.evetech.net/characters/42/portrait?size=128'
        self.assertEqual(
            eveimageserver.character_portrait_url(42, 128), expected
        )

    def test_type_icon_url(self):
        expected = 'https://images.evetech.net/types/42/icon?size=128'
        self.assertEqual(eveimageserver.type_icon_url(42, 128), expected)

    def test_type_render_url(self):
        expected = 'https://images.evetech.net/types/42/render?size=128'
        self.assertEqual(eveimageserver.type_render_url(42, 128), expected)
