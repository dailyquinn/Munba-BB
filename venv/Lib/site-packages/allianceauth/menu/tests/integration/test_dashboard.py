from http import HTTPStatus

from django.test import TestCase

from allianceauth.menu.core.smart_sync import reset_menu_items_sync
from allianceauth.menu.tests.factories import (
    create_folder_menu_item,
    create_link_menu_item,
    create_user,
)
from allianceauth.menu.tests.utils import extract_links


class TestDefaultDashboardWithSideMenu(TestCase):
    def test_should_show_all_types_of_menu_entries(self):
        # given
        user = create_user(permissions=["auth.group_management"])
        self.client.force_login(user)
        create_link_menu_item(text="Alpha", url="http://www.example.com/alpha")
        folder = create_folder_menu_item(text="Folder")
        create_link_menu_item(
            text="Bravo", url="http://www.example.com/bravo", parent=folder
        )
        reset_menu_items_sync()  # this simulates startup

        # when
        response = self.client.get("/dashboard/")

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        links = extract_links(response)
        # open_page_in_browser(response)
        self.assertEqual(links["/dashboard/"], "Dashboard")
        self.assertEqual(links["/groups/"], "Groups")
        self.assertEqual(links["/groupmanagement/requests/"], "Group Management")
        self.assertEqual(links["http://www.example.com/alpha"], "Alpha")
        self.assertEqual(links["http://www.example.com/bravo"], "Bravo")

    def test_should_not_show_menu_entry_when_user_has_no_permission(self):
        # given
        user = create_user()
        self.client.force_login(user)
        reset_menu_items_sync()

        # when
        response = self.client.get("/dashboard/")

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        links = extract_links(response)
        self.assertEqual(links["/dashboard/"], "Dashboard")
        self.assertEqual(links["/groups/"], "Groups")
        self.assertNotIn("/groupmanagement/requests/", links)

    def test_should_not_show_menu_entry_when_hidden(self):
        # given
        user = create_user()
        self.client.force_login(user)
        create_link_menu_item(text="Alpha", url="http://www.example.com/")
        reset_menu_items_sync()

        # when
        response = self.client.get("/dashboard/")

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        links = extract_links(response)
        self.assertEqual(links["/dashboard/"], "Dashboard")
        self.assertEqual(links["/groups/"], "Groups")
        self.assertNotIn("http://www.example.com/alpha", links)


class TestBS3DashboardWithSideMenu(TestCase):
    def test_should_not_show_group_management_when_user_has_no_permission(self):
        # given
        user = create_user()
        self.client.force_login(user)

        # when
        response = self.client.get("/dashboard_bs3/")

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        links = extract_links(response)
        self.assertEqual(links["/dashboard/"], "Dashboard")
        self.assertEqual(links["/groups/"], "Groups")
        self.assertNotIn("/groupmanagement/requests/", links)

    def test_should_show_group_management_when_user_has_permission(self):
        # given
        user = create_user(permissions=["auth.group_management"])
        self.client.force_login(user)

        # when
        response = self.client.get("/dashboard_bs3/")

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        links = extract_links(response)
        self.assertEqual(links["/dashboard/"], "Dashboard")
        self.assertEqual(links["/groups/"], "Groups")
        self.assertEqual(links["/groupmanagement/requests/"], "Group Management")
