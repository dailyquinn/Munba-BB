import requests_mock

from django.test.utils import override_settings

from allianceauth.analytics.tasks import (
    analytics_event,
    send_ga_tracking_celery_event)
from allianceauth.utils.testing import NoSocketsTestCase


GOOGLE_ANALYTICS_DEBUG_URL = 'https://www.google-analytics.com/debug/mp/collect'


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@requests_mock.Mocker()
class TestAnalyticsTasks(NoSocketsTestCase):
    def test_analytics_event(self, requests_mocker):
        requests_mocker.register_uri('POST', GOOGLE_ANALYTICS_DEBUG_URL)
        analytics_event(
            namespace='allianceauth.analytics',
            task='send_tests',
            label='test',
            value=1,
            result="Success",
            event_type='Stats')

    def test_send_ga_tracking_celery_event_sent(self, requests_mocker):
        # given
        requests_mocker.register_uri('POST', GOOGLE_ANALYTICS_DEBUG_URL)
        token = 'G-6LYSMYK8DE'
        secret = 'KLlpjLZ-SRGozS5f5wb_kw',
        category = 'test'
        action = 'test'
        label = 'test'
        value = '1'
        # when
        task = send_ga_tracking_celery_event(
            token,
            secret,
            category,
            action,
            label,
            value)
        # then
        self.assertEqual(task, 200)

    def test_send_ga_tracking_celery_event_success(self, requests_mocker):
        # given
        requests_mocker.register_uri(
            'POST',
            GOOGLE_ANALYTICS_DEBUG_URL,
            json={"validationMessages": []}
        )
        token = 'G-6LYSMYK8DE'
        secret = 'KLlpjLZ-SRGozS5f5wb_kw',
        category = 'test'
        action = 'test'
        label = 'test'
        value = '1'
        # when
        task = send_ga_tracking_celery_event(
            token,
            secret,
            category,
            action,
            label,
            value)
        # then
        self.assertTrue(task, 200)
