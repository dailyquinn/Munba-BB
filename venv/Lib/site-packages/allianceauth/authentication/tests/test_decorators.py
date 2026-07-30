from unittest import mock
from urllib import parse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse, URLPattern

from allianceauth.eveonline.models import EveCharacter
from allianceauth.tests.auth_utils import AuthUtils


from ..decorators import decorate_url_patterns, main_character_required
from ..models import CharacterOwnership

MODULE_PATH = 'allianceauth.authentication'


class DecoratorTestCase(TestCase):
    @staticmethod
    @main_character_required
    def dummy_view(*args, **kwargs):
        return HttpResponse(status=200)

    @classmethod
    def setUpTestData(cls):
        cls.main_user = AuthUtils.create_user('main_user', disconnect_signals=True)
        cls.no_main_user = AuthUtils.create_user(
            'no_main_user', disconnect_signals=True
        )
        main_character = EveCharacter.objects.create(
            character_id=1,
            character_name='Main Character',
            corporation_id=1,
            corporation_name='Corp',
            corporation_ticker='CORP',
        )
        CharacterOwnership.objects.create(
            user=cls.main_user, character=main_character, owner_hash='1'
        )
        cls.main_user.profile.main_character = main_character

    def setUp(self):
        self.request = RequestFactory().get('/test/')

    @mock.patch(MODULE_PATH + '.decorators.messages')
    def test_login_redirect(self, m):
        setattr(self.request, 'user', AnonymousUser())
        response = self.dummy_view(self.request)
        self.assertEqual(response.status_code, 302)
        url = getattr(response, 'url', None)
        self.assertEqual(parse.urlparse(url).path, reverse(settings.LOGIN_URL))

    @mock.patch(MODULE_PATH + '.decorators.messages')
    def test_main_character_redirect(self, m):
        setattr(self.request, 'user', self.no_main_user)
        response = self.dummy_view(self.request)
        self.assertEqual(response.status_code, 302)
        url = getattr(response, 'url', None)
        self.assertEqual(url, reverse('authentication:dashboard'))

    @mock.patch(MODULE_PATH + '.decorators.messages')
    def test_successful_request(self, m):
        setattr(self.request, 'user', self.main_user)
        response = self.dummy_view(self.request)
        self.assertEqual(response.status_code, 200)


class TestDecorateUrlPatterns(TestCase):
    def test_should_add_decorator_by_default(self):
        # given
        decorator = mock.MagicMock(name="decorator")
        view = mock.MagicMock(name="view")
        path = mock.MagicMock(spec=URLPattern, name="path")
        path.callback = view
        path.lookup_str = "my_lookup_str"
        urls = [path]
        urlconf_module = urls
        # when
        decorate_url_patterns(urlconf_module, decorator)
        # then
        self.assertEqual(path.callback, decorator(view))

    def test_should_not_add_decorator_when_excluded(self):
        # given
        decorator = mock.MagicMock(name="decorator")
        view = mock.MagicMock(name="view")
        path = mock.MagicMock(spec=URLPattern, name="path")
        path.callback = view
        path.lookup_str = "my_lookup_str"
        urls = [path]
        urlconf_module = urls
        # when
        decorate_url_patterns(urlconf_module, decorator, excluded_views=["my_lookup_str"])
        # then
        self.assertEqual(path.callback, view)
