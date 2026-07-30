from unittest.mock import patch

from django.test import TestCase

from allianceauth.menu.core import smart_sync
from allianceauth.menu.tests.factories import create_link_menu_item
from allianceauth.menu.tests.utils import PACKAGE_PATH


@patch(PACKAGE_PATH + ".models.MenuItem.objects.sync_all", spec=True)
class TestSmartSync(TestCase):
    def test_should_sync_after_reset(self, mock_sync_all):
        # given
        smart_sync.reset_menu_items_sync()
        mock_sync_all.reset_mock()

        # when
        smart_sync.sync_menu()

        # then
        self.assertTrue(mock_sync_all.called)

    def test_should_sync_when_sync_flag_is_set_but_no_items_in_db(self, mock_sync_all):
        # given
        smart_sync._record_menu_was_synced()

        # when
        smart_sync.sync_menu()

        # then
        self.assertTrue(mock_sync_all.called)

    def test_should_not_sync_when_sync_flag_is_set_and_items_in_db(self, mock_sync_all):
        # given
        smart_sync._record_menu_was_synced()
        create_link_menu_item()

        # when
        smart_sync.sync_menu()

        # then
        self.assertFalse(mock_sync_all.called)
