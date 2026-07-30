from django.test import TestCase

from allianceauth.menu.core.menu_item_hooks import (
    MenuItemHookCustom,
    gather_params,
    generate_hash,
)
from allianceauth.menu.tests.factories import create_menu_item_hook_function


class TestGenerateHash(TestCase):
    def test_should_generate_same_hash(self):
        # given
        hook = create_menu_item_hook_function()

        # when
        result_1 = generate_hash(hook())
        result_2 = generate_hash(hook())

        # then
        self.assertIsInstance(result_1, str)
        self.assertEqual(result_1, result_2)

    def test_should_generate_different_hashes(self):
        # given
        hook_1 = create_menu_item_hook_function()
        hook_2 = create_menu_item_hook_function()

        # when
        result_1 = generate_hash(hook_1())
        result_2 = generate_hash(hook_2())

        # then
        self.assertNotEqual(result_1, result_2)


class TestExtractParams(TestCase):
    def test_should_return_params(self):
        # given
        hook = create_menu_item_hook_function(text="Alpha", order=42)

        # when
        result = gather_params(hook())

        # then
        self.assertEqual(result.text, "Alpha")
        self.assertEqual(result.order, 42)
        self.assertIsInstance(result.hash, str)


class TestMenuItemHookCustom(TestCase):
    def test_should_create_minimal(self):
        # when
        obj = MenuItemHookCustom(text="text", classes="classes", url_name="url_name")

        # then
        self.assertEqual(obj.text, "text")
        self.assertEqual(obj.classes, "classes")
        self.assertEqual(obj.url_name, "url_name")
        self.assertEqual(obj.url, "")
        self.assertIsNone(obj.is_folder)
        self.assertEqual(obj.html_id, "")
        self.assertListEqual(obj.children, [])
