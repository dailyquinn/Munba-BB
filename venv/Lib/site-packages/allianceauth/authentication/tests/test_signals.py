from allianceauth.authentication.models import User, UserProfile
from allianceauth.eveonline.models import (
    EveCharacter,
    EveCorporationInfo,
    EveAllianceInfo
)
from django.db.models.signals import (
    pre_save,
    post_save,
    pre_delete,
    m2m_changed
)
from allianceauth.tests.auth_utils import AuthUtils

from django.test.testcases import TestCase
from unittest.mock import Mock
from . import patch


class TestUserProfileSignals(TestCase):

    def setUp(self):
        state = AuthUtils.get_member_state()

        self.char = EveCharacter.objects.create(
            character_id='1234',
            character_name='test character',
            corporation_id='2345',
            corporation_name='test corp',
            corporation_ticker='tickr',
            alliance_id='3456',
            alliance_name='alliance name',
        )

        self.alliance = EveAllianceInfo.objects.create(
            alliance_id='3456',
            alliance_name='alliance name',
            alliance_ticker='TIKR',
            executor_corp_id='2345',
        )

        self.corp = EveCorporationInfo.objects.create(
            corporation_id='2345',
            corporation_name='corp name',
            corporation_ticker='TIKK',
            member_count=10,
            alliance=self.alliance,
        )

        state.member_alliances.add(self.alliance)
        state.member_corporations.add(self.corp)

        self.member = AuthUtils.create_user('test user')
        self.member.profile.main_character = self.char
        self.member.profile.save()

    @patch('.signals.create_required_models')
    def test_create_required_models_triggered_true(
            self, create_required_models):
        """
        Create a User object here,
        to generate UserProfile models
        """
        post_save.connect(create_required_models, sender=User)
        AuthUtils.create_user('test_create_required_models_triggered')
        self.assertTrue = create_required_models.called
        self.assertEqual(create_required_models.call_count, 1)

        user = User.objects.get(username='test_create_required_models_triggered')
        self.assertIsNot(UserProfile.objects.get(user=user), False)

    @patch('.signals.create_required_models')
    def test_create_required_models_triggered_false(
            self, create_required_models):
        """
        Only call a User object Update here,
        which does not need to generate UserProfile models
        """
        post_save.connect(create_required_models, sender=User)
        char = EveCharacter.objects.create(
            character_id='1266',
            character_name='test character2',
            corporation_id='2345',
            corporation_name='test corp',
            corporation_ticker='tickr',
            alliance_id='3456',
            alliance_name='alliance name',
        )
        self.member.profile.main_character = char
        self.member.profile.save()

        self.assertTrue = create_required_models.called
        self.assertEqual(create_required_models.call_count, 0)
        self.assertIsNot(UserProfile.objects.get(user=self.member), False)
