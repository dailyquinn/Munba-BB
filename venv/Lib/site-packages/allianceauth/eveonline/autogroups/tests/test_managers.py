from allianceauth.eveonline.models import EveCorporationInfo
from django.test import TestCase
from allianceauth.tests.auth_utils import AuthUtils

from ..models import AutogroupsConfig
from . import patch


class AutogroupsConfigManagerTestCase(TestCase):

    def test_update_groups_for_state(self):
        member = AuthUtils.create_member('test member')
        obj = AutogroupsConfig.objects.create()
        obj.states.add(member.profile.state)

        with patch('.models.AutogroupsConfig.update_group_membership_for_user') as update_group_membership_for_user:
            AutogroupsConfig.objects.update_groups_for_state(member.profile.state)

            self.assertTrue(update_group_membership_for_user.called)
            self.assertEqual(update_group_membership_for_user.call_count, 1)
            args, kwargs = update_group_membership_for_user.call_args
            self.assertEqual(args[0], member)

    def test_update_groups_for_user(self):
        member = AuthUtils.create_member('test member')
        obj = AutogroupsConfig.objects.create()
        obj.states.add(member.profile.state)

        with patch('.models.AutogroupsConfig.update_group_membership_for_user') \
        as update_group_membership_for_user:
            AutogroupsConfig.objects.update_groups_for_user(
                user=member
            )

            self.assertTrue(update_group_membership_for_user.called)
            self.assertEqual(update_group_membership_for_user.call_count, 1)
            args, kwargs = update_group_membership_for_user.call_args
            self.assertEqual(args[0], member)

    def test_update_groups_for_user_no_state(self):
        member = AuthUtils.create_member('test member')
        obj = AutogroupsConfig.objects.create()
        obj.states.add(member.profile.state)

        with patch('.models.AutogroupsConfig.update_group_membership_for_user') \
        as update_group_membership_for_user:
            AutogroupsConfig.objects.update_groups_for_user(
                user=member,
                state=member.profile.state
            )

            self.assertTrue(update_group_membership_for_user.called)
            self.assertEqual(update_group_membership_for_user.call_count, 1)
            args, kwargs = update_group_membership_for_user.call_args
            self.assertEqual(args[0], member)


    @patch('.models.AutogroupsConfig.update_group_membership_for_user')
    @patch('.models.AutogroupsConfig.remove_user_from_alliance_groups')
    @patch('.models.AutogroupsConfig.remove_user_from_corp_groups')
    def test_update_groups_no_config(self, remove_corp, remove_alliance, update_groups):
        member = AuthUtils.create_member('test member')
        obj = AutogroupsConfig.objects.create()

        # Corp and alliance groups should be removed from users if their state has no config
        AutogroupsConfig.objects.update_groups_for_user(member)

        self.assertFalse(update_groups.called)
        self.assertTrue(remove_alliance.called)
        self.assertTrue(remove_corp.called)

        # The normal group assignment should occur if there state has a config
        obj.states.add(member.profile.state)
        AutogroupsConfig.objects.update_groups_for_user(member)

        self.assertTrue(update_groups.called)

    def test_update_group_membership_corp_in_two_configs(self):
        # given
        member = AuthUtils.create_member('test member')
        AuthUtils.add_main_character_2(
            member,
            character_id='1234',
            name='test character',
            corp_id='2345',
            corp_name='corp name',
            corp_ticker='TIKK',

        )

        corp = EveCorporationInfo.objects.create(
            corporation_id='2345',
            corporation_name='corp name',
            corporation_ticker='TIKK',
            member_count=10,
        )

        member_state = AuthUtils.get_member_state()
        member_config = AutogroupsConfig.objects.create(corp_groups=True)
        member_config.states.add(member_state)
        blue_state = AuthUtils.get_blue_state()
        blue_state.member_corporations.add(corp)
        blue_config = AutogroupsConfig.objects.create(corp_groups=True)
        blue_config.states.add(blue_state)

        member.profile.state = blue_state
        member.profile.save()

        AutogroupsConfig.objects.update_groups_for_user(member)

        # Checks before test that the role is correctly applied
        group = blue_config.get_corp_group(corp)
        self.assertIn(group, member.groups.all())

        # when
        blue_state.member_corporations.remove(corp)
        member_state.member_corporations.add(corp)
        member.profile.state = member_state
        member.profile.save()

        # then
        AutogroupsConfig.objects.update_groups_for_user(member)
        group = member_config.get_corp_group(corp)
        self.assertIn(group, member.groups.all())
