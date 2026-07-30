"""
Example Test
"""

# Django
from django.test import TestCase
from django.utils import timezone

# Django EVE SDE
from eve_sde.models import EveSDE
from eve_sde.sde_tasks import process_from_sde


class TestExample(TestCase):
    """
    TestExample
    """

    def test_load(self):
        """
        Test Loading SDE
        :return:
        :rtype:
        """
        now = timezone.now()
        process_from_sde()
        self.assertLess(now, EveSDE.get_solo().last_check_date)
