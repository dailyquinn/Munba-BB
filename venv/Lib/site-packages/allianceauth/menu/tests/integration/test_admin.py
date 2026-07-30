from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from allianceauth.menu.constants import MenuItemType
from allianceauth.menu.forms import (
    AppMenuItemAdminForm,
    FolderMenuItemAdminForm,
    LinkMenuItemAdminForm,
)
from allianceauth.menu.models import MenuItem
from allianceauth.menu.tests.factories import (
    create_app_menu_item,
    create_folder_menu_item,
    create_link_menu_item,
    create_user,
)
from allianceauth.menu.tests.utils import extract_html


def extract_menu_item_texts(response):
    """Extract labels of menu items shown in change list."""
    soup = extract_html(response)
    items = soup.find_all("th", {"class": "field-_text"})
    labels = {elem.text for elem in items}
    return labels


class TestAdminSite(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = create_user(is_superuser=True, is_staff=True)
        cls.changelist_url = reverse("admin:menu_menuitem_changelist")
        cls.add_url = reverse("admin:menu_menuitem_add")

    def change_url(self, id_):
        return reverse("admin:menu_menuitem_change", args=[id_])

    def test_changelist_should_show_all_types(self):
        # given
        self.client.force_login(self.user)
        create_app_menu_item(text="app")
        create_folder_menu_item(text="folder")
        create_link_menu_item(text="link")

        # when
        response = self.client.get(self.changelist_url)

        # then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        labels = extract_menu_item_texts(response)
        self.assertSetEqual(labels, {"app", "[folder]", "link"})

    def test_should_create_new_link_item(self):
        # given
        self.client.force_login(self.user)

        # when
        response = self.client.post(
            self.add_url,
            {"text": "alpha", "url": "http://www.example.com", "order": 99},
        )
        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.text, "alpha")
        self.assertEqual(obj.item_type, MenuItemType.LINK)

    def test_should_create_new_folder_item(self):
        # given
        self.client.force_login(self.user)

        # when
        response = self.client.post(
            self.add_url + "?type=folder", {"text": "alpha", "order": 99}
        )
        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.text, "alpha")
        self.assertEqual(obj.item_type, MenuItemType.FOLDER)

    def test_should_change_app_item(self):
        # given
        self.client.force_login(self.user)
        item = create_app_menu_item(text="alpha", order=1)
        form_data = AppMenuItemAdminForm(instance=item).initial
        form_data["order"] = 99
        form_data["parent"] = ""

        # when
        response = self.client.post(self.change_url(item.id), form_data)

        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.order, 99)
        self.assertEqual(obj.item_type, MenuItemType.APP)

    def test_should_change_link_item(self):
        # given
        self.client.force_login(self.user)
        item = create_link_menu_item(text="alpha")
        form_data = LinkMenuItemAdminForm(instance=item).initial
        form_data["text"] = "bravo"
        form_data["parent"] = ""

        # when
        response = self.client.post(self.change_url(item.id), form_data)

        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.text, "bravo")
        self.assertEqual(obj.item_type, MenuItemType.LINK)

    def test_should_change_folder_item(self):
        # given
        self.client.force_login(self.user)
        item = create_folder_menu_item(text="alpha")
        form_data = FolderMenuItemAdminForm(instance=item).initial
        form_data["text"] = "bravo"

        # when
        response = self.client.post(self.change_url(item.id), form_data)

        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.text, "bravo")
        self.assertEqual(obj.item_type, MenuItemType.FOLDER)

    def test_should_move_item_into_folder(self):
        # given
        self.client.force_login(self.user)
        link = create_link_menu_item(text="alpha")
        folder = create_folder_menu_item(text="folder")
        form_data = LinkMenuItemAdminForm(instance=link).initial
        form_data["parent"] = folder.id

        # when
        response = self.client.post(self.change_url(link.id), form_data)

        # then
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.changelist_url)
        link.refresh_from_db()
        self.assertEqual(link.parent, folder)

    def test_should_filter_items_by_type(self):
        # given
        self.client.force_login(self.user)
        create_app_menu_item(text="app")
        create_folder_menu_item(text="folder")
        create_link_menu_item(text="link")

        # when
        cases = [("link", "link"), ("app", "app"), ("folder", "[folder]")]
        for filter_name, expected_label in cases:
            with self.subTest(filter_name=filter_name):
                response = self.client.get(self.changelist_url + f"?type={filter_name}")

                # then
                self.assertEqual(response.status_code, HTTPStatus.OK)
                labels = extract_menu_item_texts(response)
                self.assertSetEqual(labels, {expected_label})
