from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from allianceauth.groupmanagement.models import Group, GroupRequest
from allianceauth.tests.auth_utils import AuthUtils

from .. import views


def response_content_to_str(response) -> str:
    return response.content.decode(response.charset)


class TestViews(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = AuthUtils.create_user('Peter Parker')
        self.user_with_manage_permission = AuthUtils.create_user('Bruce Wayne')
        self.group = Group.objects.create(name="Example group")

        # set permissions
        AuthUtils.add_permission_to_user_by_name(
            'auth.group_management', self.user_with_manage_permission
        )

    def test_groups_view_can_load(self):
        request = self.factory.get(reverse('groupmanagement:groups'))
        request.user = self.user
        response = views.groups_view(request)
        self.assertEqual(response.status_code, 200)

    def test_management_view_can_load_for_user_with_permissions(self):
        """
        Test if user with management permissions can access the management view
        :return:
        """

        request = self.factory.get(reverse('groupmanagement:management'))
        request.user = self.user_with_manage_permission
        response = views.group_management(request)
        self.assertEqual(response.status_code, 200)

    def test_management_view_doesnt_load_for_user_without_permissions(self):
        """
        Test if user without management permissions can't access the management view
        :return:
        """

        request = self.factory.get(reverse('groupmanagement:management'))
        request.user = self.user
        response = views.group_management(request)
        self.assertEqual(response.status_code, 302)

    @override_settings(GROUPMANAGEMENT_AUTO_LEAVE=False)
    def test_leave_requests_tab_visible(self):
        """
        Test if the leave requests tab is visible when GROUPMANAGEMENT_AUTO_LEAVE = False
        :return:
        """

        request = self.factory.get(reverse('groupmanagement:management'))
        request.user = self.user_with_manage_permission
        response = views.group_management(request)

        content = response_content_to_str(response)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="leave-tab" data-bs-toggle="tab" data-bs-target="#leave"', content)
        self.assertIn('<div id="leave" class="tab-pane">', content)

    @override_settings(GROUPMANAGEMENT_AUTO_LEAVE=True)
    def test_leave_requests_tab_hidden(self):
        """
        Test if the leave requests tab is hidden when GROUPMANAGEMENT_AUTO_LEAVE = True
        :return:
        """

        request = self.factory.get(reverse('groupmanagement:management'))
        request.user = self.user_with_manage_permission
        response = views.group_management(request)

        content = response_content_to_str(response)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id="leave-tab" data-bs-toggle="tab" data-bs-target="#leave"', content)
        self.assertNotIn('<div id="leave" class="tab-pane">', content)

    @override_settings(GROUPMANAGEMENT_AUTO_LEAVE=True)
    def test_should_not_hide_leave_requests_tab_when_there_are_open_requests(self):
        # given
        request = self.factory.get(reverse('groupmanagement:management'))
        request.user = self.user_with_manage_permission
        GroupRequest.objects.create(user=self.user, group=self.group, leave_request=True)

        # when
        response = views.group_management(request)

        # then
        content = response_content_to_str(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<a class="nav-link" id="leave-tab" data-bs-toggle="tab" data-bs-target="#leave"', content)
        self.assertIn('<div id="leave" class="tab-pane">', content)
