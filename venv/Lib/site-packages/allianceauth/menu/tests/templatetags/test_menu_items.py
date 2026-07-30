from unittest.mock import patch

from django.test import RequestFactory, TestCase

from allianceauth.menu.templatetags.menu_items import render_menu
from allianceauth.menu.tests.factories import create_menu_item_hook_function
from allianceauth.menu.tests.utils import PACKAGE_PATH, render_template

MODULE_PATH = PACKAGE_PATH + ".templatetags.menu_items"


class TestTemplateTags(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()

    @patch(MODULE_PATH + ".render_menu", spec=True)
    def test_menu_items(self, mock_render_menu):
        # given
        mock_render_menu.return_value = ["Alpha"]
        request = self.factory.get("/")

        # when
        rendered = render_template(
            "{% load menu_items %}{% menu_items %}",
            context={"request": request},
        )
        self.assertIn("Alpha", rendered)


@patch(MODULE_PATH + ".get_hooks", spec=True)
class TestRenderMenu(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_should_render_menu_in_order(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = [
            create_menu_item_hook_function(text="Charlie"),
            create_menu_item_hook_function(text="Alpha", order=1),
            create_menu_item_hook_function(text="Bravo", order=2),
        ]
        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 3)
        self.assertIn("Alpha", menu[0])
        self.assertIn("Bravo", menu[1])
        self.assertIn("Charlie", menu[2])
