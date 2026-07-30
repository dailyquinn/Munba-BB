from typing import List, NamedTuple, Optional
from unittest.mock import patch

from bs4 import BeautifulSoup

from django.test import RequestFactory, TestCase

from allianceauth.menu.templatetags.menu_menu_items import (
    RenderedMenuItem,
    render_menu,
)
from allianceauth.menu.tests.factories import (
    create_app_menu_item,
    create_folder_menu_item,
    create_link_menu_item,
    create_menu_item_from_hook,
    create_menu_item_hook_class,
    create_menu_item_hook_function,
    create_rendered_menu_item,
)
from allianceauth.menu.tests.utils import (
    PACKAGE_PATH,
    remove_whitespaces,
    render_template,
)

MODULE_PATH = PACKAGE_PATH + ".templatetags.menu_menu_items"


class TestTemplateTags(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()

    @patch(MODULE_PATH + ".render_menu", spec=True)
    @patch(MODULE_PATH + ".smart_sync.sync_menu", spec=True)
    def test_sorted_menu_items(self, mock_sync_menu, mock_render_menu):
        # given
        fake_item = {"html": "Alpha"}
        mock_render_menu.return_value = [fake_item]
        request = self.factory.get("/")

        # when
        rendered = render_template(
            "{% load menu_menu_items %}{% menu_items %}",
            context={"request": request},
        )
        self.assertIn("Alpha", rendered)
        self.assertTrue(mock_sync_menu.called)


@patch(MODULE_PATH + ".get_hooks", spec=True)
class TestRenderDefaultMenu(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()

    def test_should_render_app_menu_items(self, mock_get_hooks):
        # given
        menu = [
            create_menu_item_hook_function(text="Charlie", count=42),
            create_menu_item_hook_function(text="Alpha", order=1),
            create_menu_item_hook_function(text="Bravo", order=2),
        ]
        mock_get_hooks.return_value = menu
        for hook in menu:
            create_menu_item_from_hook(hook)

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 3)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Bravo")
        self.assertEqual(menu[2].menu_item.text, "Charlie")
        self.assertEqual(menu[2].count, 42)
        attrs = parse_html(menu[2])
        self.assertEqual(attrs.count, 42)
        self.assertEqual(attrs.text, "Charlie")

    def test_should_render_link_menu_items(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = []
        create_link_menu_item(text="Charlie"),
        create_link_menu_item(text="Alpha", order=1),
        create_link_menu_item(text="Bravo", order=2),

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 3)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Bravo")
        self.assertEqual(menu[2].menu_item.text, "Charlie")
        attrs = parse_html(menu[2])
        self.assertEqual(attrs.text, "Charlie")

    def test_should_render_folders(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = []
        folder = create_folder_menu_item(text="Folder", order=2)
        create_link_menu_item(text="Alpha", order=1)
        create_link_menu_item(text="Bravo", order=3)
        create_link_menu_item(text="Charlie", parent=folder)

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 3)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Folder")
        self.assertEqual(menu[2].menu_item.text, "Bravo")

        self.assertEqual(menu[1].children[0].menu_item.text, "Charlie")
        attrs = parse_html(menu[1].children[0])
        self.assertEqual(attrs.text, "Charlie")

    def test_should_render_folder_properties(self, mock_get_hooks):
        # given
        # given
        menu = [
            create_menu_item_hook_function(text="Charlie", count=42),
            create_menu_item_hook_function(text="Alpha", count=5),
            create_menu_item_hook_function(text="Bravo"),
        ]
        mock_get_hooks.return_value = menu

        folder = create_folder_menu_item(text="Folder", order=1)
        for hook in menu:
            create_menu_item_from_hook(hook, parent=folder)

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 1)
        item = menu[0]
        self.assertEqual(item.menu_item.text, "Folder")
        self.assertEqual(item.count, 47)
        self.assertTrue(item.is_folder)
        self.assertEqual(len(item.children), 3)
        attrs = parse_html(item)
        self.assertEqual(attrs.count, 47)
        self.assertIn("fa-folder", attrs.classes)

    def test_should_remove_empty_folders(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = []
        create_folder_menu_item(text="Folder", order=2)
        create_link_menu_item(text="Alpha", order=1)
        create_link_menu_item(text="Bravo", order=3)

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 2)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Bravo")

    def test_should_remove_empty_folders_with_items_hidden(self, mock_get_hooks):
        # given

        class TestHook(create_menu_item_hook_class()):
            text = "Dummy App No Data"
            classes = "fa-solid fa-users-gear"
            url_name = "groupmanagement:management"

            def render(Self, request):
                # simulate no perms
                return ""

        params = {
            "text": "Alpha",
            "classes": "fa-solid fa-users-gear",
            "url_name": "groupmanagement:management",
        }

        alpha = TestHook(**params)

        hooks = [lambda: alpha]

        mock_get_hooks.return_value = hooks

        folder = create_folder_menu_item(text="Folder", order=2)
        create_menu_item_from_hook(hooks[0], parent=folder)
        create_link_menu_item(text="Bravo", order=3)  # this is all that should show

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 1)
        self.assertEqual(menu[0].menu_item.text, "Bravo")

    def test_should_not_include_hidden_items(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = []
        create_link_menu_item(text="Charlie"),
        create_link_menu_item(text="Alpha", order=1),
        create_link_menu_item(text="Bravo", order=2, is_hidden=True),

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 2)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Charlie")

    def test_should_not_render_hidden_folders(self, mock_get_hooks):
        # given
        menu = [
            create_menu_item_hook_function(text="Charlie", count=42),
            create_menu_item_hook_function(text="Alpha", count=5),
            create_menu_item_hook_function(text="Bravo"),
        ]
        mock_get_hooks.return_value = menu

        folder = create_folder_menu_item(text="Folder", order=1, is_hidden=True)
        for hook in menu:
            create_menu_item_from_hook(hook, parent=folder)

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 0)

    def test_should_allow_several_items_with_same_text(self, mock_get_hooks):
        # given
        mock_get_hooks.return_value = []
        create_link_menu_item(text="Alpha", order=1),
        create_link_menu_item(text="Alpha", order=2),

        request = self.factory.get("/")

        # when
        result = render_menu(request)

        # then
        menu = list(result)
        self.assertEqual(len(menu), 2)
        self.assertEqual(menu[0].menu_item.text, "Alpha")
        self.assertEqual(menu[1].menu_item.text, "Alpha")


class TestRenderedMenuItem(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()
        cls.template = "menu/menu-item-bs5.html"

    def test_create_from_menu_item_with_defaults(self):
        # given
        item = create_link_menu_item()

        # when
        obj = RenderedMenuItem(menu_item=item)

        # then
        self.assertEqual(obj.menu_item, item)
        self.assertIsNone(obj.count)
        self.assertEqual(obj.html, "")
        self.assertEqual(obj.html_id, "")
        self.assertListEqual(obj.children, [])

    def test_should_identify_if_item_is_a_folder(self):
        # given
        app_item = create_rendered_menu_item(menu_item=create_app_menu_item())
        link_item = create_rendered_menu_item(menu_item=create_link_menu_item())
        folder_item = create_rendered_menu_item(menu_item=create_folder_menu_item())

        cases = [
            (app_item, False),
            (link_item, False),
            (folder_item, True),
        ]
        # when
        for obj, expected in cases:
            with self.subTest(type=expected):
                self.assertIs(obj.is_folder, expected)

    def test_should_update_html_for_link_item(self):
        # given
        obj = create_rendered_menu_item(menu_item=create_link_menu_item(text="Alpha"))
        request = self.factory.get("/")

        # when
        obj.update_html(request, self.template)

        # then
        parsed = parse_html(obj)
        self.assertEqual(parsed.text, "Alpha")
        self.assertIsNone(parsed.count)
        self.assertFalse(obj.html_id)

    def test_should_update_html_for_folder_item(self):
        # given
        request = self.factory.get("/")
        folder_item = create_folder_menu_item(text="Alpha")
        link_item = create_link_menu_item(text="Bravo", parent=folder_item)
        obj = create_rendered_menu_item(menu_item=folder_item, count=42)
        rendered_link = create_rendered_menu_item(menu_item=link_item)
        rendered_link.update_html(request, self.template)
        obj.children.append(rendered_link)

        # when
        obj.update_html(request, self.template)

        # then
        self.assertTrue(obj.html_id)
        parsed_parent = parse_html(obj)
        self.assertEqual(parsed_parent.text, "Alpha")
        self.assertEqual(parsed_parent.count, 42)
        self.assertIn("Bravo", obj.html)


class _ParsedMenuItem(NamedTuple):
    classes: List[str]
    text: str
    count: Optional[int]


def parse_html(obj: RenderedMenuItem) -> _ParsedMenuItem:
    soup = BeautifulSoup(obj.html, "html.parser")
    classes = soup.li.i.attrs["class"]
    text = remove_whitespaces(soup.li.a.text)
    try:
        count = int(remove_whitespaces(soup.li.span.text))
    except (AttributeError, ValueError):
        count = None

    return _ParsedMenuItem(classes=classes, text=text, count=count)
