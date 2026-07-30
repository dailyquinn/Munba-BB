from django.test import TestCase

from allianceauth.menu.constants import DEFAULT_FOLDER_ICON_CLASSES
from allianceauth.menu.forms import FolderMenuItemAdminForm


class TestFolderMenuItemAdminForm(TestCase):
    def test_should_set_default_icon_classes(self):
        # given
        form_data = {"text": "Alpha", "order": 1}
        form = FolderMenuItemAdminForm(data=form_data)

        # when
        obj = form.save(commit=False)

        # then
        self.assertEqual(obj.classes, DEFAULT_FOLDER_ICON_CLASSES)

    def test_should_use_icon_classes_from_input(self):
        # given
        form_data = {"text": "Alpha", "order": 1, "classes": "dummy"}
        form = FolderMenuItemAdminForm(data=form_data)

        # when
        obj = form.save(commit=False)

        # then
        self.assertEqual(obj.classes, "dummy")
