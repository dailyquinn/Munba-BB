from django.test import TestCase
from allianceauth.tests.auth_utils import AuthUtils

from ..models import NameFormatConfig


class TestNameFormatConfig(TestCase):

    def test_str(self):
        obj = NameFormatConfig.objects.create(
            service_name='mumble',
            format='{{character_name}}'
        )
        obj.states.add(AuthUtils.get_member_state())
        obj.states.add(AuthUtils.get_guest_state())
        expected = 'mumble: Member, Guest'
        self.assertEqual(str(obj), expected)
