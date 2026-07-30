from unittest import TestCase
from unittest.mock import patch, MagicMock
from django.urls import URLPattern

from allianceauth.services.hooks import UrlHook
from allianceauth.urls import urls_from_apps

MODULE_PATH = "allianceauth.urls"


@patch(MODULE_PATH + ".main_character_required")
@patch(MODULE_PATH + ".decorate_url_patterns")
class TestUrlsFromApps(TestCase):
    def test_should_decorate_url_by_default(self, mock_decorate_url_patterns, mock_main_character_required):
        # given
        def hook_function():
            return UrlHook(urlconf_module, "my_namespace", r"^my_app/")

        view = MagicMock(name="view")
        path = MagicMock(spec=URLPattern, name="path")
        path.callback = view
        urlconf_module = [patch], "my_app"
        # when
        result = urls_from_apps([hook_function], [])
        # then
        self.assertIsInstance(result[0], URLPattern)
        self.assertTrue(mock_decorate_url_patterns.called)
        args, _ = mock_decorate_url_patterns.call_args
        decorator = args[1]
        self.assertEqual(decorator, mock_main_character_required)
        excluded_views = args[2]
        self.assertIsNone(excluded_views)

    def test_should_not_decorate_when_excluded(self, mock_decorate_url_patterns, mock_main_character_required):
        # given
        def hook_function():
            return UrlHook(urlconf_module, "my_namespace", r"^my_app/", ["excluded_view"])

        view = MagicMock(name="view")
        path = MagicMock(spec=URLPattern, name="path")
        path.callback = view
        urlconf_module = [patch], "my_app"
        # when
        result = urls_from_apps([hook_function], ["my_app"])
        # then
        self.assertIsInstance(result[0], URLPattern)
        self.assertTrue(mock_decorate_url_patterns.called)
        args, _ = mock_decorate_url_patterns.call_args
        decorator = args[1]
        self.assertEqual(decorator, mock_main_character_required)
        excluded_views = args[2]
        self.assertSetEqual(excluded_views, {"excluded_view"})

    def test_should_decorate_when_app_has_no_permission(self, mock_decorate_url_patterns, mock_main_character_required):
        # given
        def hook_function():
            return UrlHook(urlconf_module, "my_namespace", r"^my_app/", ["excluded_view"])

        view = MagicMock(name="view")
        path = MagicMock(spec=URLPattern, name="path")
        path.callback = view
        urlconf_module = [patch], "my_app"
        # when
        result = urls_from_apps([hook_function], ["other_app"])
        # then
        self.assertIsInstance(result[0], URLPattern)
        self.assertTrue(mock_decorate_url_patterns.called)
        args, _ = mock_decorate_url_patterns.call_args
        decorator = args[1]
        self.assertEqual(decorator, mock_main_character_required)
        excluded_views = args[2]
        self.assertIsNone(excluded_views)
