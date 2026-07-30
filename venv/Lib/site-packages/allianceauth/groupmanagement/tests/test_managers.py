from django.contrib.auth.models import Group, User
from django.test import TestCase

from allianceauth.eveonline.models import EveCorporationInfo, EveAllianceInfo
from allianceauth.tests.auth_utils import AuthUtils

from ..models import GroupRequest
from ..managers import GroupManager


class MockUserNotAuthenticated():
    def __init__(self):
        self.is_authenticated = False


class GroupManagementVisibilityTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('test')
        AuthUtils.add_main_character(
            cls.user, 'test character', '1', corp_id='2', corp_name='test_corp', corp_ticker='TEST', alliance_id='3', alliance_name='TEST'
        )
        cls.user.profile.refresh_from_db()
        cls.alliance = EveAllianceInfo.objects.create(alliance_id='3', alliance_name='test alliance', alliance_ticker='TEST', executor_corp_id='2')
        cls.corp = EveCorporationInfo.objects.create(
            corporation_id='2', corporation_name='test corp', corporation_ticker='TEST', alliance=cls.alliance, member_count=1
        )
        cls.group1 = Group.objects.create(name='group1')
        cls.group2 = Group.objects.create(name='group2')
        cls.group3 = Group.objects.create(name='group3')

    def setUp(self):
        self.user.refresh_from_db()

    def _refresh_user(self):
        self.user = User.objects.get(pk=self.user.pk)

    def test_get_group_leaders_groups(self):
        self.group1.authgroup.group_leaders.add(self.user)
        self.group2.authgroup.group_leader_groups.add(self.group1)
        self._refresh_user()
        groups = GroupManager.get_group_leaders_groups(self.user)

        self.assertIn(self.group1, groups)  # avail due to user
        self.assertNotIn(self.group2, groups)  # not avail due to group
        self.assertNotIn(self.group3, groups)  # not avail at all

        self.user.groups.add(self.group1)
        self._refresh_user()
        groups = GroupManager.get_group_leaders_groups(self.user)

    def test_can_manage_group(self):
        self.group1.authgroup.group_leaders.add(self.user)
        self.user.groups.add(self.group1)
        self._refresh_user()

        self.assertTrue(GroupManager.can_manage_group(self.user, self.group1))
        self.assertFalse(GroupManager.can_manage_group(self.user, self.group2))
        self.assertFalse(GroupManager.can_manage_group(self.user, self.group3))

        self.group2.authgroup.group_leader_groups.add(self.group1)
        self.group1.authgroup.group_leaders.remove(self.user)
        self._refresh_user()

        self.assertFalse(GroupManager.can_manage_group(self.user, self.group1))
        self.assertTrue(GroupManager.can_manage_group(self.user, self.group2))
        self.assertFalse(GroupManager.can_manage_group(self.user, self.group3))


class TestGroupManager(TestCase):
    def setUp(self) -> None:
        # group 1
        self.group_default = Group.objects.create(name='default')
        self.group_default.authgroup.description = 'Default Group'
        self.group_default.authgroup.internal = False
        self.group_default.authgroup.hidden = False
        self.group_default.authgroup.save()

        # group 2
        self.group_internal = Group.objects.create(name='internal')
        self.group_internal.authgroup.description = 'Internal Group'
        self.group_internal.authgroup.internal = True
        self.group_internal.authgroup.save()

        # group 3
        self.group_hidden = Group.objects.create(name='hidden')
        self.group_hidden.authgroup.description = 'Hidden Group'
        self.group_hidden.authgroup.internal = False
        self.group_hidden.authgroup.hidden = True
        self.group_hidden.authgroup.save()

        # group 4
        self.group_open = Group.objects.create(name='open')
        self.group_open.authgroup.description = 'Open Group'
        self.group_open.authgroup.internal = False
        self.group_open.authgroup.hidden = False
        self.group_open.authgroup.open = True
        self.group_open.authgroup.save()

        # group 5
        self.group_public_1 = Group.objects.create(name='public 1')
        self.group_public_1.authgroup.description = 'Public Group 1'
        self.group_public_1.authgroup.internal = False
        self.group_public_1.authgroup.hidden = False
        self.group_public_1.authgroup.public = True
        self.group_public_1.authgroup.save()

        # group 6
        self.group_public_2 = Group.objects.create(name='public 2')
        self.group_public_2.authgroup.description = 'Public Group 2'
        self.group_public_2.authgroup.internal = False
        self.group_public_2.authgroup.hidden = True
        self.group_public_2.authgroup.open = True
        self.group_public_2.authgroup.public = True
        self.group_public_2.authgroup.save()

        # group 7
        self.group_default_member = Group.objects.create(name='default members')
        self.group_default_member.authgroup.description = \
            'Default Group for members only'
        self.group_default_member.authgroup.internal = False
        self.group_default_member.authgroup.hidden = False
        self.group_default_member.authgroup.open = False
        self.group_default_member.authgroup.public = False
        self.group_default_member.authgroup.states.add(
            AuthUtils.get_member_state()
        )
        self.group_default_member.authgroup.save()

        # user
        self.user = AuthUtils.create_user('Bruce Wayne')

    def test_get_joinable_group_member(self):
        result = GroupManager.get_joinable_groups(
            AuthUtils.get_member_state()
        )
        expected = {
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2,
            self.group_default_member
        }
        self.assertSetEqual(set(result), expected)

    def test_get_joinable_group_guest(self):
        result = GroupManager.get_joinable_groups(
            AuthUtils.get_guest_state()
        )
        expected = {
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2
        }
        self.assertSetEqual(set(result), expected)

    def test_joinable_group_member(self):
        member_state = AuthUtils.get_member_state()
        for x in [
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2,
            self.group_default_member
        ]:
            self.assertTrue(GroupManager.joinable_group(x, member_state))

        for x in [
            self.group_internal,
        ]:
            self.assertFalse(GroupManager.joinable_group(x, member_state))

    def test_joinable_group_guest(self):
        guest_state = AuthUtils.get_guest_state()
        for x in [
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2
        ]:
            self.assertTrue(GroupManager.joinable_group(x, guest_state))

        for x in [
            self.group_internal,
            self.group_default_member
        ]:
            self.assertFalse(GroupManager.joinable_group(x, guest_state))

    def test_get_all_non_internal_groups(self):
        result = GroupManager.get_all_non_internal_groups()
        expected = {
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2,
            self.group_default_member
        }
        self.assertSetEqual(set(result), expected)

    def test_check_internal_group(self):
        self.assertTrue(
            GroupManager.check_internal_group(self.group_default)
        )
        self.assertFalse(
            GroupManager.check_internal_group(self.group_internal)
        )

    def test_get_joinable_groups_for_user_no_permission(self):
        AuthUtils.assign_state(self.user, AuthUtils.get_guest_state())
        result = GroupManager.get_joinable_groups_for_user(self.user)
        expected = {self.group_public_1, self.group_public_2}
        self.assertSetEqual(set(result), expected)

    def test_get_joinable_groups_for_user_guest_w_permission_(self):
        AuthUtils.assign_state(self.user, AuthUtils.get_guest_state())
        AuthUtils.add_permission_to_user_by_name(
            'groupmanagement.request_groups', self.user
        )
        result = GroupManager.get_joinable_groups_for_user(self.user)
        expected = {
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2
        }
        self.assertSetEqual(set(result), expected)

    def test_get_joinable_groups_for_user_member_w_permission(self):
        AuthUtils.assign_state(self.user, AuthUtils.get_member_state(), True)
        self.user = AuthUtils.add_permission_to_user_by_name(
            'groupmanagement.request_groups', self.user
        )
        result = GroupManager.get_joinable_groups_for_user(self.user)
        expected = {
            self.group_default,
            self.group_hidden,
            self.group_open,
            self.group_public_1,
            self.group_public_2,
            self.group_default_member
        }
        self.assertSetEqual(set(result), expected)

    def test_get_joinable_groups_for_user_member_w_permission_no_hidden(self):
        AuthUtils.assign_state(self.user, AuthUtils.get_member_state(), True)
        self.user = AuthUtils.add_permission_to_user_by_name(
            'groupmanagement.request_groups', self.user
        )
        result = GroupManager.get_joinable_groups_for_user(
            self.user, include_hidden=False
        )
        expected = {
            self.group_default,
            self.group_open,
            self.group_public_1,
            self.group_default_member
        }
        self.assertSetEqual(set(result), expected)

    def test_has_management_permission(self):
        user = AuthUtils.create_user('Clark Kent')
        user = AuthUtils.add_permission_to_user_by_name(
            'auth.group_management', user
        )
        self.assertTrue(GroupManager.has_management_permission(user))

    def test_can_manage_groups_no_perm_no_group(self):
        user = AuthUtils.create_user('Clark Kent')
        self.assertFalse(GroupManager.can_manage_groups(user))

    def test_can_manage_groups_user_not_authenticated(self):
        user = MockUserNotAuthenticated()
        self.assertFalse(GroupManager.can_manage_groups(user))

    def test_can_manage_groups_has_perm(self):
        user = AuthUtils.create_user('Clark Kent')
        user = AuthUtils.add_permission_to_user_by_name(
            'auth.group_management', user
        )
        self.assertTrue(GroupManager.can_manage_groups(user))

    def test_can_manage_groups_no_perm_leads_group(self):
        user = AuthUtils.create_user('Clark Kent')
        self.group_default.authgroup.group_leaders.add(user)
        self.assertTrue(GroupManager.can_manage_groups(user))

    def test_can_manage_group_no_perm_no_group(self):
        user = AuthUtils.create_user('Clark Kent')
        self.assertFalse(
            GroupManager.can_manage_group(user, self.group_default)
        )

    def test_can_manage_group_has_perm(self):
        user = AuthUtils.create_user('Clark Kent')
        user = AuthUtils.add_permission_to_user_by_name(
            'auth.group_management', user
        )
        self.assertTrue(
            GroupManager.can_manage_group(user, self.group_default)
        )

    def test_can_manage_group_no_perm_leads_correct_group(self):
        user = AuthUtils.create_user('Clark Kent')
        self.group_default.authgroup.group_leaders.add(user)
        self.assertTrue(
            GroupManager.can_manage_group(user, self.group_default)
        )

    def test_can_manage_group_no_perm_leads_other_group(self):
        user = AuthUtils.create_user('Clark Kent')
        self.group_hidden.authgroup.group_leaders.add(user)
        self.assertFalse(
            GroupManager.can_manage_group(user, self.group_default)
        )

    def test_can_manage_group_user_not_authenticated(self):
        user = MockUserNotAuthenticated()
        self.assertFalse(
            GroupManager.can_manage_group(user, self.group_default)
        )


class TestPendingRequestsCountForUser(TestCase):

    def setUp(self) -> None:
        self.group_1 = Group.objects.create(name="Group 1")
        self.group_2 = Group.objects.create(name="Group 2")
        self.group_3 = Group.objects.create(name="Group 3")

        self.user_leader_1 = AuthUtils.create_member('Clark Kent')
        self.group_1.authgroup.group_leaders.add(self.user_leader_1)
        self.user_leader_2 = AuthUtils.create_member('Peter Parker')
        self.group_2.authgroup.group_leaders.add(self.user_leader_2)

        self.user_requestor = AuthUtils.create_member('Bruce Wayne')
        self.user_superuser = AuthUtils.create_member('Q')
        self.user_superuser.is_superuser = True

    def test_single_request_for_leader(self):
        # given user_leader_1 is leader of group_1
        # and user_leader_2 is leader of group_2
        # when user_requestor is requesting access to group 1
        # then return 1 for user_leader 1 and 0 for user_leader_2
        GroupRequest.objects.create(
            user=self.user_requestor, group=self.group_1
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_leader_1), 1
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_leader_2), 0
        )

    def test_return_none_for_none_leader(self):
        # given user_requestor is leader of no group
        # when user_requestor is requesting access to group 1
        # then return 0 for user_requestor
        GroupRequest.objects.create(
            user=self.user_requestor, group=self.group_1
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_requestor), 0
        )

    def test_single_request_for_superuser(self):
        # given group_3 has no leader
        # when user_requestor is requesting access to group 1
        # then return 1 for user_superuser but 0 for user_requestor
        GroupRequest.objects.create(
            user=self.user_requestor, group=self.group_3
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_superuser), 1
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_requestor), 0
        )

    def test_single_leave_request(self):
        # given user_leader_2 is leader of group_2
        # and user_requestor is member of group 2
        # when user_requestor is requesting to leave group 2
        # then return 1 for user_leader_2
        self.user_requestor.groups.add(self.group_2)

        GroupRequest.objects.create(
            user=self.user_requestor,
            group=self.group_2,
            leave_request=True
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_leader_2), 1
        )

    def test_join_and_leave_request(self):
        # given user_leader_2 is leader of group_2
        # and user_requestor is member of group 2
        # when user_requestor is requesting to leave group 2
        # and user_requestor_2 is requesting to join group 2
        # then return 2 for user_leader_2
        self.user_requestor.groups.add(self.group_2)
        user_requestor_2 = AuthUtils.create_member("Lex Luther")
        GroupRequest.objects.create(
            user=user_requestor_2,
            group=self.group_2
        )
        GroupRequest.objects.create(
            user=self.user_requestor,
            group=self.group_2,
            leave_request=True
        )
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_leader_2), 2
        )

    def test_single_request_for_user_with_management_perm(self):
        # given user_leader_4 which is leafer of no group
        # but has the management permissions
        # when user_requestor is requesting access to group 1
        # then return 1 for user_leader_4
        user_leader_4 = AuthUtils.create_member("Lex Luther")
        user_leader_4 = AuthUtils.add_permission_to_user_by_name(
            "auth.group_management", user_leader_4
        )
        GroupRequest.objects.create(user=self.user_requestor, group=self.group_1)
        self.assertEqual(
            GroupManager.pending_requests_count_for_user(self.user_leader_1), 1
        )

    def test_single_request_for_members_of_leading_group(self):
        # given
        leader_group = Group.objects.create(name="Leaders")
        self.group_3.authgroup.group_leader_groups.add(leader_group)
        self.user_leader_1.groups.add(leader_group)
        GroupRequest.objects.create(user=self.user_requestor, group=self.group_3)
        # when
        result = GroupManager.pending_requests_count_for_user(self.user_leader_1)
        # then
        self.assertEqual(result, 1)
