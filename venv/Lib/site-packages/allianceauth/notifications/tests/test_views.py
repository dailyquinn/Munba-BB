import json

from unittest.mock import patch, Mock

from django.test import TestCase, RequestFactory
from django.urls import reverse

from allianceauth.tests.auth_utils import AuthUtils

from ..views import user_notifications_count


MODULE_PATH = 'allianceauth.notifications.views'


class TestViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.create_user('magic_mike')
        AuthUtils.add_main_character(
            cls.user,
            'Magic Mike',
            '1',
            corp_id='2',
            corp_name='Pole Riders',
            corp_ticker='PRIDE',
            alliance_id='3',
            alliance_name='RIDERS'
        )
        cls.factory = RequestFactory()

    @patch(MODULE_PATH + '.Notification.objects.user_unread_count')
    def test_user_notifications_count(self, mock_user_unread_count):
        unread_count = 42
        user_pk = 3
        mock_user_unread_count.return_value = unread_count

        request = self.factory.get(
            reverse('notifications:user_notifications_count', args=[user_pk])
        )
        request.user = self.user

        response = user_notifications_count(request, user_pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_user_unread_count.called)
        expected = {'unread_count': unread_count}
        result = json.loads(response.content.decode(response.charset))
        self.assertDictEqual(result, expected)
