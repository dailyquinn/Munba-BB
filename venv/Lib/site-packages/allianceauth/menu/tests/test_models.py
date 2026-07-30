from django.test import TestCase

from allianceauth.menu.constants import MenuItemType

from .factories import (
    create_app_menu_item,
    create_folder_menu_item,
    create_link_menu_item,
)


class TestMenuItem(TestCase):
    def test_str(self):
        # given
        obj = create_link_menu_item()
        # when
        result = str(obj)
        # then
        self.assertIsInstance(result, str)

    def test_should_return_item_type(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        cases = [
            (app_item, MenuItemType.APP),
            (link_item, MenuItemType.LINK),
            (folder_item, MenuItemType.FOLDER),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertEqual(obj.item_type, expected)

    def test_should_identify_if_item_is_a_child(self):
        # given
        folder = create_folder_menu_item()
        child = create_link_menu_item(parent=folder)
        not_child = create_link_menu_item()

        cases = [(child, True), (not_child, False)]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_child, expected)

    def test_should_identify_if_item_is_a_folder(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        cases = [
            (app_item, False),
            (link_item, False),
            (folder_item, True),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_folder, expected)

    def test_should_identify_if_item_is_user_defined(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        cases = [
            (app_item, False),
            (link_item, True),
            (folder_item, True),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_user_defined, expected)

    def test_should_identify_if_item_is_an_app_item(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        cases = [
            (app_item, True),
            (link_item, False),
            (folder_item, False),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_app_item, expected)

    def test_should_identify_if_item_is_a_link_item(self):
        # given
        app_item = create_app_menu_item()
        link_item = create_link_menu_item()
        folder_item = create_folder_menu_item()

        cases = [
            (app_item, False),
            (link_item, True),
            (folder_item, False),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_link_item, expected)

    def test_should_not_allow_creating_invalid_app_item(self):
        # when
        obj = create_app_menu_item(hook_hash="")

        # then
        obj.refresh_from_db()
        self.assertIsNone(obj.hook_hash)


class TestMenuItemToHookObj(TestCase):
    def test_should_create_from_link_item(self):
        # given
        obj = create_link_menu_item(text="Alpha")

        # when
        hook_obj = obj.to_hook_obj()

        # then
        self.assertEqual(hook_obj.text, "Alpha")
        self.assertEqual(hook_obj.url, obj.url)
        self.assertEqual(hook_obj.html_id, "")
        self.assertFalse(hook_obj.is_folder)

    def test_should_create_from_folder(self):
        # given
        obj = create_folder_menu_item(text="Alpha", classes="dummy")

        # when
        hook_obj = obj.to_hook_obj()

        # then
        self.assertEqual(hook_obj.text, "Alpha")
        self.assertEqual(hook_obj.classes, "dummy")
        self.assertEqual(hook_obj.url, "")
        self.assertTrue(hook_obj.html_id)
        self.assertTrue(hook_obj.is_folder)

    def test_should_create_from_folder_and_use_default_icon_classes(self):
        # given
        obj = create_folder_menu_item(classes="")

        # when
        hook_obj = obj.to_hook_obj()

        # then
        self.assertEqual(hook_obj.classes, "fa-solid fa-folder")

    def test_should_create_from_app_item(self):
        # given
        obj = create_app_menu_item(text="Alpha")

        # when
        with self.assertRaises(ValueError):
            obj.to_hook_obj()
