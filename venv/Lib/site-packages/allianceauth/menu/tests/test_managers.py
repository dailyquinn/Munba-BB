from unittest.mock import patch

from django.db.models import QuerySet
from django.test import TestCase

from allianceauth.menu.constants import MenuItemType
from allianceauth.menu.models import MenuItem

from .factories import (
    create_app_menu_item,
    create_folder_menu_item,
    create_link_menu_item,
    create_menu_item_from_hook,
    create_menu_item_hook_function,
)
from .utils import PACKAGE_PATH


class TestMenuItemQuerySet(TestCase):
    def test_should_add_item_type_field(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        # when
        result: QuerySet[MenuItem] = MenuItem.objects.annotate_item_type_2()

        # then
        for obj in [app_item, link_item, folder_item]:
            obj = result.get(pk=app_item.pk)
            self.assertEqual(obj.item_type_2, obj.item_type)

    def test_should_filter_folders(self):
        # given
        create_app_menu_item()
        create_link_menu_item()
        folder_item = create_folder_menu_item()

        # when
        result: QuerySet[MenuItem] = MenuItem.objects.filter_folders()

        # then
        item_pks = set(result.values_list("pk", flat=True))
        self.assertSetEqual(item_pks, {folder_item.pk})


@patch(PACKAGE_PATH + ".managers.get_hooks", spec=True)
class TestMenuItemManagerSyncAll(TestCase):
    def test_should_create_new_items_from_hooks_when_they_do_not_exist(
        self, mock_get_hooks
    ):
        # given
        mock_get_hooks.return_value = [create_menu_item_hook_function(text="Alpha")]

        # when
        MenuItem.objects.sync_all()

        # then
        self.assertEqual(MenuItem.objects.count(), 1)
        obj = MenuItem.objects.first()
        self.assertEqual(obj.item_type, MenuItemType.APP)
        self.assertEqual(obj.text, "Alpha")

    def test_should_update_existing_app_items_when_changed_only(self, mock_get_hooks):
        # given
        menu_hook_1 = create_menu_item_hook_function(text="Alpha", order=1)
        menu_hook_2 = create_menu_item_hook_function(text="Bravo", order=2)
        mock_get_hooks.return_value = [menu_hook_1, menu_hook_2]
        create_menu_item_from_hook(menu_hook_1, text="name has changed", order=99)
        create_menu_item_from_hook(menu_hook_2)

        # when
        MenuItem.objects.sync_all()

        # then
        self.assertEqual(MenuItem.objects.count(), 2)

        obj = MenuItem.objects.get(text="Alpha")
        self.assertEqual(obj.item_type, MenuItemType.APP)
        self.assertEqual(obj.order, 99)

        obj = MenuItem.objects.get(text="Bravo")
        self.assertEqual(obj.item_type, MenuItemType.APP)
        self.assertEqual(obj.order, 2)

    def test_should_remove_obsolete_app_items_but_keep_user_items(self, mock_get_hooks):
        # given
        menu_hook = create_menu_item_hook_function(text="Alpha")
        mock_get_hooks.return_value = [menu_hook]
        create_app_menu_item(text="Bravo")  # obsolete item
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        # when
        MenuItem.objects.sync_all()

        # then
        self.assertEqual(MenuItem.objects.count(), 3)
        obj = MenuItem.objects.get(text="Alpha")
        self.assertTrue(obj.item_type, MenuItemType.APP)
        self.assertIn(link_item, MenuItem.objects.all())
        self.assertIn(folder_item, MenuItem.objects.all())
