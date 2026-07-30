from django.test import TestCase
from django.contrib.auth.models import User, Group

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.eveonline.autogroups.models import AutogroupsConfig
from allianceauth.tests.auth_utils import AuthUtils


from ..models import ReservedGroupName


class TestGroupSignals(TestCase):
    def test_should_create_authgroup_when_group_is_created(self):
        # when
        group = Group.objects.create(name="test")
        # then
        self.assertEqual(group.authgroup.group, group)

    def test_should_rename_group_that_conflicts_with_reserved_name(self):
        # given
        ReservedGroupName.objects.create(name="test", reason="dummy", created_by="xyz")
        ReservedGroupName.objects.create(name="test_1", reason="dummy", created_by="xyz")
        # when
        group = Group.objects.create(name="Test")
        # then
        self.assertNotEqual(group.name, "test")
        self.assertNotEqual(group.name, "test_1")


class TestCheckGroupsOnStateChange(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('test')
        cls.character = AuthUtils.add_main_character_2(
            cls.user, 'test character', 1001, corp_id=2001, corp_name='test corp 1', corp_ticker='TEST'
        )
        cls.user.profile.refresh_from_db()
        cls.corp_1 = EveCorporationInfo.objects.create(
            corporation_id=2001, corporation_name='test corp 1', corporation_ticker='C1', member_count=1
        )
        cls.corp_2 = EveCorporationInfo.objects.create(
            corporation_id=2002, corporation_name='test corp 2', corporation_ticker='C2', member_count=1
        )
        cls.guest_state = AuthUtils.get_guest_state()
        cls.test_state_1 = AuthUtils.create_state('test_state_1', 500)
        cls.test_state_2 = AuthUtils.create_state('test_state_2', 600)

    def setUp(self):
        self.user.refresh_from_db()

    def _refresh_user(self):
        self.user = User.objects.get(pk=self.user.pk)

    def test_drop_state_group(self):
        """
        given user is member of: state group, normal group and auto group
        when user looses state
        then user is automatically kicked from state group
        and remains member of normal group and auto group
        """
        # setup
        state_group = Group.objects.create(name='state_group')
        state_group.authgroup.states.add(self.test_state_1)
        state_group.authgroup.internal = False
        state_group.save()
        normal_group = Group.objects.create(name='normal_group')
        normal_group.authgroup.internal = False
        normal_group.save()
        internal_group = Group.objects.create(name='internal_group')
        autogroup_config = AutogroupsConfig.objects.create(corp_groups=True)
        autogroup_config.states.add(self.test_state_1)
        autogroup_config.states.add(self.guest_state)
        auto_group = autogroup_config.corp_managed_groups.first()
        internal_state_group = Group.objects.create(name='internal_state_group')
        internal_state_group.authgroup.states.add(self.test_state_1)
        self.test_state_1.member_corporations.add(self.corp_1)
        self.user.groups.add(normal_group)
        self.user.groups.add(internal_group)
        self.user.groups.add(state_group)
        self.user.groups.add(internal_state_group)

        # user changes state back to guest
        self.test_state_1.member_corporations.clear()

        # assert
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.guest_state)
        groups = self.user.groups.all()
        self.assertNotIn(state_group, groups)  # looses state group
        self.assertNotIn(internal_state_group, groups)  # looses state group
        self.assertIn(normal_group, groups)  # normal group unafected
        self.assertIn(internal_group, groups)  # internal group unafected
        self.assertIn(auto_group, groups)  # auto group unafected

    def test_change_to_other_state(self):
        """
        given a state group with 2 allowed states
        when user changes from one state to the other
        then user remains member of that group
        """
        # setup
        state_group = Group.objects.create(name='state_group')
        state_group.authgroup.states.add(self.test_state_1)
        state_group.authgroup.states.add(self.test_state_2)

        self.test_state_1.member_corporations.add(self.corp_1)
        self.test_state_2.member_corporations.add(self.corp_2)
        self.user.groups.add(state_group)

        # user changes state back to guest
        self.character.corporation_id = 2002
        self.character.corporation_name = "test corp 2"
        self.character.save()

        # assert
        self._refresh_user()
        self.assertEqual(self.user.profile.state, self.test_state_2)
        groups = self.user.groups.all()
        self.assertIn(state_group, groups)
