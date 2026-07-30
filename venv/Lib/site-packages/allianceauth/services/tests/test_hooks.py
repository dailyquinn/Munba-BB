from unittest import TestCase

from allianceauth.services.hooks import UrlHook
from allianceauth.groupmanagement import urls


class TestUrlHook(TestCase):
    def test_can_create_simple_hook(self):
        # when
        obj = UrlHook(urls, "groupmanagement", r"^groupmanagement/")
        # then
        self.assertEqual(obj.include_pattern.app_name, "groupmanagement")
        self.assertFalse(obj.excluded_views)

    def test_can_create_hook_with_excluded_views(self):
        # when
        obj = UrlHook(
            urls,
            "groupmanagement",
            r"^groupmanagement/",
            ["groupmanagement.views.group_management"],
        )
        # then
        self.assertEqual(obj.include_pattern.app_name, "groupmanagement")
        self.assertIn("groupmanagement.views.group_management", obj.excluded_views)

    def test_should_raise_error_when_called_with_invalid_excluded_views(self):
        # when/then
        with self.assertRaises(TypeError):
            UrlHook(urls, "groupmanagement", r"^groupmanagement/", 99)
