from unittest import mock

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from allianceauth.tests.auth_utils import AuthUtils

from ..models import GroupRequest, RequestLog, ReservedGroupName

MODULE_PATH = "allianceauth.groupmanagement.models"


def create_testdata():
    # group 1
    group = Group.objects.create(name='Superheros')
    group.authgroup.description = 'Default Group'
    group.authgroup.internal = False
    group.authgroup.hidden = False
    group.authgroup.save()
    # user 1
    user_1 = AuthUtils.create_user('Bruce Wayne')
    AuthUtils.add_main_character_2(
        user_1,
        name='Bruce Wayne',
        character_id=1001,
        corp_id=2001,
        corp_name='Wayne Technologies'
    )
    user_1.groups.add(group)
    group.authgroup.group_leaders.add(user_1)
    # user 2
    user_2 = AuthUtils.create_user('Clark Kent')
    AuthUtils.add_main_character_2(
        user_2,
        name='Clark Kent',
        character_id=1002,
        corp_id=2002,
        corp_name='Wayne Food'
    )
    # user 3
    user_3 = AuthUtils.create_user('Peter Parker')
    AuthUtils.add_main_character_2(
        user_2,
        name='Peter Parker',
        character_id=1003,
        corp_id=2002,
        corp_name='Wayne Food'
    )
    return group, user_1, user_2, user_3


class TestGroupRequest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group, cls.user_1, cls.user_2, cls.user_3 = create_testdata()

    def test_main_char(self):
        group_request = GroupRequest.objects.create(
            user=self.user_1,
            group=self.group
        )
        expected = self.user_1.profile.main_character
        self.assertEqual(group_request.main_char, expected)

    def test_str(self):
        group_request = GroupRequest.objects.create(
            user=self.user_1,
            group=self.group
        )
        expected = 'Bruce Wayne:Superheros'
        self.assertEqual(str(group_request), expected)

    @override_settings(GROUPMANAGEMENT_REQUESTS_NOTIFICATION=True)
    def test_should_notify_leaders_about_join_request(self):
        # given
        group_request = GroupRequest.objects.create(
            user=self.user_2, group=self.group
        )
        # when
        with mock.patch(MODULE_PATH + ".notify") as mock_notify:
            group_request.notify_leaders()
        # then
        self.assertTrue(mock_notify.called)
        _, kwargs = mock_notify.call_args
        self.assertEqual(kwargs["user"],self.user_1)

    @override_settings(GROUPMANAGEMENT_REQUESTS_NOTIFICATION=True)
    def test_should_notify_leaders_about_leave_request(self):
        # given
        group_request = GroupRequest.objects.create(
            user=self.user_2, group=self.group
        )
        # when
        with mock.patch(MODULE_PATH + ".notify") as mock_notify:
            group_request.notify_leaders()
        # then
        self.assertTrue(mock_notify.called)

    @override_settings(GROUPMANAGEMENT_REQUESTS_NOTIFICATION=True)
    def test_should_handle_notify_leaders_without_leaders(self):
        # given
        group = Group.objects.create(name='Dummy')
        group.authgroup.internal = False
        group.authgroup.hidden = False
        group.authgroup.save()
        group_request = GroupRequest.objects.create(
            user=self.user_2, group=group
        )
        # when
        with mock.patch(MODULE_PATH + ".notify") as mock_notify:
            group_request.notify_leaders()
        # then
        self.assertFalse(mock_notify.called)

    @override_settings(GROUPMANAGEMENT_REQUESTS_NOTIFICATION=False)
    def test_should_not_notify_leaders_if_disabled(self):
        # given
        group_request = GroupRequest.objects.create(
            user=self.user_2, group=self.group
        )
        # when
        with mock.patch(MODULE_PATH + ".notify") as mock_notify:
            group_request.notify_leaders()
        # then
        self.assertFalse(mock_notify.called)

    @override_settings(GROUPMANAGEMENT_REQUESTS_NOTIFICATION=True)
    def test_should_notify_members_of_leader_groups_about_join_request(self):
        # given
        child_group = Group.objects.create(name='Child')
        child_group.authgroup.internal = False
        child_group.authgroup.hidden = False
        child_group.authgroup.save()
        child_group.authgroup.group_leader_groups.add(self.group)
        group_request = GroupRequest.objects.create(
            user=self.user_2, group=child_group
        )
        # when
        with mock.patch(MODULE_PATH + ".notify") as mock_notify:
            group_request.notify_leaders()
        # then
        self.assertTrue(mock_notify.called)
        _, kwargs = mock_notify.call_args
        self.assertEqual(kwargs["user"],self.user_1)


class TestRequestLog(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group, cls.user_1, cls.user_2, _ = create_testdata()

    def test_requestor(self):
        request_log = RequestLog.objects.create(
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1
        )
        expected = 'Clark Kent'
        self.assertEqual(request_log.requestor(), expected)

    def test_type_to_str_removed(self):
        request_log = RequestLog.objects.create(
            request_type=None,
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1
        )
        expected = 'Removed'
        self.assertEqual(request_log.type_to_str(), expected)

    def test_type_to_str_leave(self):
        request_log = RequestLog.objects.create(
            request_type=True,
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1
        )
        expected = 'Leave'
        self.assertEqual(request_log.type_to_str(), expected)

    def test_type_to_str_join(self):
        request_log = RequestLog.objects.create(
            request_type=False,
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1
        )
        expected = 'Join'
        self.assertEqual(request_log.type_to_str(), expected)

    def test_action_to_str_accept(self):
        request_log = RequestLog.objects.create(
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1,
            action=True
        )
        expected = 'Accept'
        self.assertEqual(request_log.action_to_str(), expected)

    def test_action_to_str_reject(self):
        request_log = RequestLog.objects.create(
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1,
            action=False
        )
        expected = 'Reject'
        self.assertEqual(request_log.action_to_str(), expected)

    def test_req_char(self):
        request_log = RequestLog.objects.create(
            group=self.group,
            request_info='Clark Kent:Superheros',
            request_actor=self.user_1,
            action=False
        )
        expected = self.user_2.profile.main_character
        self.assertEqual(request_log.req_char(), expected)


class TestAuthGroup(TestCase):
    def test_str(self):
        group = Group.objects.create(name='Superheros')
        group.authgroup.description = 'Default Group'
        group.authgroup.internal = False
        group.authgroup.hidden = False
        group.authgroup.save()

        expected = 'Superheros'
        self.assertEqual(str(group.authgroup), expected)

    def test_should_remove_guests_from_group_when_restricted_to_members_only(self):
        # given
        user_member = AuthUtils.create_user("Bruce Wayne")
        character_member = AuthUtils.add_main_character_2(
            user_member,
            name="Bruce Wayne",
            character_id=1001,
            corp_id=2001,
            corp_name="Wayne Technologies",
        )
        user_guest = AuthUtils.create_user("Lex Luthor")
        AuthUtils.add_main_character_2(
            user_guest,
            name="Lex Luthor",
            character_id=1011,
            corp_id=2011,
            corp_name="Luthor Corp",
        )
        member_state = AuthUtils.get_member_state()
        member_state.member_characters.add(character_member)
        user_member.refresh_from_db()
        user_guest.refresh_from_db()
        group = Group.objects.create(name="dummy")
        user_member.groups.add(group)
        user_guest.groups.add(group)
        group.authgroup.states.add(member_state)
        # when
        group.authgroup.remove_users_not_matching_states()
        # then
        self.assertIn(group, user_member.groups.all())
        self.assertNotIn(group, user_guest.groups.all())


class TestAuthGroupRequestApprovers(TestCase):
    def setUp(self) -> None:
        self.group, self.user_1, self.user_2, self.user_3 = create_testdata()

    def test_should_return_leaders_of_main_group_only(self):
        # when
        leaders = self.group.authgroup.group_request_approvers()
        # then
        self.assertSetEqual(leaders, {self.user_1})

    def test_should_return_members_of_leading_groups_only(self):
        # given
        parent_group = Group.objects.create(name='Parent')
        parent_group.authgroup.group_leaders.add(self.user_2)
        self.user_1.groups.add(parent_group)
        child_group = Group.objects.create(name='Child')
        child_group.authgroup.internal = False
        child_group.authgroup.hidden = False
        child_group.authgroup.save()
        child_group.authgroup.group_leader_groups.add(parent_group)
        # when
        leaders = child_group.authgroup.group_request_approvers()
        # then
        self.assertSetEqual(leaders, {self.user_1})

    def test_should_return_leaders_of_main_group_and_members_of_leading_groups(self):
        # given
        parent_group = Group.objects.create(name='Parent')
        parent_group.authgroup.group_leaders.add(self.user_2)
        self.user_1.groups.add(parent_group)
        child_group = Group.objects.create(name='Child')
        child_group.authgroup.internal = False
        child_group.authgroup.hidden = False
        child_group.authgroup.save()
        child_group.authgroup.group_leaders.add(self.user_3)
        child_group.authgroup.group_leader_groups.add(self.group)
        # when
        leaders = child_group.authgroup.group_request_approvers()
        # then
        self.assertSetEqual(leaders, {self.user_1, self.user_3})

    def test_can_handle_group_without_leaders(self):
        # given
        child_group = Group.objects.create(name='Child')
        child_group.authgroup.internal = False
        child_group.authgroup.hidden = False
        child_group.authgroup.save()
        # when
        leaders = child_group.authgroup.group_request_approvers()
        # then
        self.assertSetEqual(leaders, set())


class TestReservedGroupName(TestCase):
    def test_should_return_name(self):
        # given
        obj = ReservedGroupName(name="test", reason="abc", created_by="xxx")
        # when
        result = str(obj)
        # then
        self.assertEqual(result, "test")

    def test_should_not_allow_creating_reserved_name_for_existing_group(self):
        # given
        Group.objects.create(name="Dummy")
        # when
        with self.assertRaises(RuntimeError):
            ReservedGroupName.objects.create(
                name="dummy", reason="abc", created_by="xxx"
            )
