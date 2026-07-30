from unittest import mock
from allianceauth.authentication.middleware import UserSettingsMiddleware
from unittest.mock import Mock
from django.http import HttpResponse

from django.test.testcases import TestCase


class TestUserSettingsMiddlewareSaveLang(TestCase):

    def setUp(self):
        self.middleware = UserSettingsMiddleware(HttpResponse)
        self.request = Mock()
        self.request.headers = {
                "User-Agent": "AUTOMATED TEST"
            }
        self.request.path = '/i18n/setlang/'
        self.request.POST = {
            'language': 'fr'
        }
        self.request.user.profile.language = 'de'
        self.request.user.is_anonymous = False
        self.response = Mock()
        self.response.content = 'hello world'

    def test_middleware_passthrough(self):
        """
        Simply tests the middleware runs cleanly
        """
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.response, response)

    def test_middleware_save_language_false_anonymous(self):
        """
        Ensures the middleware wont change the usersettings
        of a non-existent (anonymous) user
        """
        self.request.user.is_anonymous = True
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.user.profile.language, 'de')
        self.assertFalse(self.request.user.profile.save.called)
        self.assertEqual(self.request.user.profile.save.call_count, 0)

    def test_middleware_save_language_new(self):
        """
        does the middleware change a language not set in the DB
        """
        self.request.user.profile.language = None
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.user.profile.language, 'fr')
        self.assertTrue(self.request.user.profile.save.called)
        self.assertEqual(self.request.user.profile.save.call_count, 1)

    def test_middleware_save_language_changed(self):
        """
        Tests the middleware will change a language setting
        """
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.user.profile.language, 'fr')
        self.assertTrue(self.request.user.profile.save.called)
        self.assertEqual(self.request.user.profile.save.call_count, 1)


class TestUserSettingsMiddlewareLoginFlow(TestCase):

    def setUp(self):
        self.middleware = UserSettingsMiddleware(HttpResponse)
        self.request = Mock()
        self.request.headers = {
                "User-Agent": "AUTOMATED TEST"
            }
        self.request.path = '/sso/login'
        self.request.session = {
            'NIGHT_MODE': False
        }
        self.request.LANGUAGE_CODE = 'en'
        self.request.user.profile.language = 'de'
        self.request.user.profile.night_mode = True
        self.request.user.profile.minimize_sidebar = False
        self.request.user.is_anonymous = False
        self.response = Mock()
        self.response.content = 'hello world'

    def test_middleware_passthrough(self):
        """
        Simply tests the middleware runs cleanly
        """
        middleware_response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.response, middleware_response)

    def test_middleware_sets_language_cookie_true_no_cookie(self):
        """
        tests the middleware will set a cookie, while none is set
        """
        self.request.LANGUAGE_CODE = None
        middleware_response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertTrue(middleware_response.set_cookie.called)
        self.assertEqual(middleware_response.set_cookie.call_count, 1)
        args, kwargs = middleware_response.set_cookie.call_args
        self.assertEqual(kwargs['value'], 'de')

    def test_middleware_sets_language_cookie_true_wrong_cookie(self):
        """
        tests the middleware will set a cookie, while a different value is set
        """
        middleware_response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertTrue(middleware_response.set_cookie.called)
        self.assertEqual(middleware_response.set_cookie.call_count, 1)
        args, kwargs = middleware_response.set_cookie.call_args
        self.assertEqual(kwargs['value'], 'de')

    def test_middleware_sets_language_cookie_false_anonymous(self):
        """
        ensures the middleware wont set a value for a non existent user (anonymous)
        """
        self.request.user.is_anonymous = True
        middleware_response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertFalse = middleware_response.set_cookie.called
        self.assertEqual(middleware_response.set_cookie.call_count, 0)

    def test_middleware_sets_language_cookie_false_already_set(self):
        """
        tests the middleware skips setting the cookie, if its already set correctly
        """
        self.request.user.profile.language = 'en'
        middleware_response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertFalse = middleware_response.set_cookie.called
        self.assertEqual(middleware_response.set_cookie.call_count, 0)

    def test_middleware_sets_night_mode_not_set(self):
        """
        tests the middleware will set night_mode if not set
        """
        self.request.session = {}
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.session["NIGHT_MODE"], True)

    def test_middleware_sets_night_mode_set(self):
        """
        tests the middleware will set night_mode if set.
        """
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.session["NIGHT_MODE"], True)

    def test_middleware_set_mimimize_sidebar(self):
        """
        tests the middleware will always set minimize_sidebar to False (default)
        """

        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.session["MINIMIZE_SIDEBAR"], False)

    def test_middleware_minimize_sidebar_when_set(self):
        """
        tests the middleware will set mimimize_sidebar to True from DB
        """

        self.request.user.profile.minimize_sidebar = True
        response = self.middleware.process_response(
            self.request,
            self.response
            )
        self.assertEqual(self.request.session["MINIMIZE_SIDEBAR"], True)
