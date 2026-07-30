from unittest import mock

from celery_once import AlreadyQueued

from django.core.cache import cache
from django.test import override_settings, TestCase

from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.services.tasks import validate_services, update_groups_for_user

from ..tasks import DjangoBackend


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class ServicesTasksTestCase(TestCase):
    def setUp(self):
        self.member = AuthUtils.create_user('auth_member')

    @mock.patch('allianceauth.services.tasks.ServicesHook')
    def test_validate_services(self, services_hook):
        # given
        svc = mock.Mock()
        svc.validate_user.return_value = None
        services_hook.get_services.return_value = [svc]
        # when
        validate_services.delay(self.member.pk)
        # then
        self.assertTrue(services_hook.get_services.called)
        self.assertTrue(svc.validate_user.called)
        args, _ = svc.validate_user.call_args
        self.assertEqual(self.member, args[0])  # Assert correct user is passed to service hook function

    @mock.patch('allianceauth.services.tasks.ServicesHook')
    def test_update_groups_for_user(self, services_hook):
        # given
        svc = mock.Mock()
        svc.validate_user.return_value = None
        services_hook.get_services.return_value = [svc]
        # when
        update_groups_for_user.delay(self.member.pk)
        # then
        self.assertTrue(services_hook.get_services.called)
        self.assertTrue(svc.validate_user.called)
        args, _ = svc.validate_user.call_args
        self.assertEqual(self.member, args[0])  # Assert correct user
        self.assertTrue(svc.update_groups.called)
        args, _ = svc.update_groups.call_args
        self.assertEqual(self.member, args[0])  # Assert correct user


class TestDjangoBackend(TestCase):

    TEST_KEY = "my-django-backend-test-key"
    TIMEOUT = 1800

    def setUp(self) -> None:
        cache.delete(self.TEST_KEY)
        self.backend = DjangoBackend(dict())

    def test_can_get_lock(self):
        """
        when lock can be acquired
        then set it with timetout
        """
        self.backend.raise_or_lock(self.TEST_KEY, self.TIMEOUT)
        self.assertIsNotNone(cache.get(self.TEST_KEY))
        self.assertAlmostEqual(cache.ttl(self.TEST_KEY), self.TIMEOUT, delta=2)

    def test_when_cant_get_lock_raise_exception(self):
        """
        when lock can bot be acquired
        then raise AlreadyQueued exception with countdown
        """
        self.backend.raise_or_lock(self.TEST_KEY, self.TIMEOUT)

        try:
            self.backend.raise_or_lock(self.TEST_KEY, self.TIMEOUT)
        except Exception as ex:
            self.assertIsInstance(ex, AlreadyQueued)
            self.assertAlmostEqual(ex.countdown, self.TIMEOUT, delta=2)

    def test_can_clear_lock(self):
        """
        when a lock exists
        then can get a new lock after clearing it
        """
        self.backend.raise_or_lock(self.TEST_KEY, self.TIMEOUT)

        self.backend.clear_lock(self.TEST_KEY)
        self.backend.raise_or_lock(self.TEST_KEY, self.TIMEOUT)
        self.assertIsNotNone(cache.get(self.TEST_KEY))
