from django.test import RequestFactory, TestCase

from allianceauth.menu.hooks import MenuItemHook

from .factories import create_menu_item_hook


class TestMenuItemHook(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.factory = RequestFactory()

    def test_should_create_obj_with_minimal_params(self):
        # when
        obj = MenuItemHook("text", "classes", "url-name")

        # then
        self.assertEqual(obj.text, "text")
        self.assertEqual(obj.classes, "classes")
        self.assertEqual(obj.url_name, "url-name")
        self.assertEqual(obj.template, "public/menuitem.html")
        self.assertEqual(obj.order, 9999)
        self.assertListEqual(obj.navactive, ["url-name"])
        self.assertIsNone(obj.count)

    def test_should_create_obj_with_full_params_1(self):
        # when
        obj = MenuItemHook("text", "classes", "url-name", 5, ["navactive"])

        # then
        self.assertEqual(obj.text, "text")
        self.assertEqual(obj.classes, "classes")
        self.assertEqual(obj.url_name, "url-name")
        self.assertEqual(obj.template, "public/menuitem.html")
        self.assertEqual(obj.order, 5)
        self.assertListEqual(obj.navactive, ["navactive", "url-name"])
        self.assertIsNone(obj.count)

    def test_should_create_obj_with_full_params_2(self):
        # when
        obj = MenuItemHook(
            text="text",
            classes="classes",
            url_name="url-name",
            order=5,
            navactive=["navactive"],
        )

        # then
        self.assertEqual(obj.text, "text")
        self.assertEqual(obj.classes, "classes")
        self.assertEqual(obj.url_name, "url-name")
        self.assertEqual(obj.template, "public/menuitem.html")
        self.assertEqual(obj.order, 5)
        self.assertListEqual(obj.navactive, ["navactive", "url-name"])
        self.assertIsNone(obj.count)

    def test_should_render_menu_item(self):
        # given
        request = self.factory.get("/")
        hook = create_menu_item_hook(text="Alpha")

        # when
        result = hook.render(request)

        # then
        self.assertIn("Alpha", result)

    def test_str(self):
        # given
        hook = create_menu_item_hook(text="Alpha")

        # when/then
        self.assertEqual(str(hook), "Alpha")

    def test_repr(self):
        # given
        hook = create_menu_item_hook(text="Alpha")

        # when/then
        self.assertIn("Alpha", repr(hook))
