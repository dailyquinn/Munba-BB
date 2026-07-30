from allianceauth.analytics.models import AnalyticsIdentifier

from django.test.testcases import TestCase

from uuid import uuid4


# Identifiers
uuid_1 = "ab33e241fbf042b6aa77c7655a768af7"
uuid_2 = "7aa6bd70701f44729af5e3095ff4b55c"


class TestAnalyticsIdentifier(TestCase):

    def test_identifier_random(self):
        self.assertNotEqual(AnalyticsIdentifier.get_solo(), uuid4)
