from unittest.mock import patch

from django.test import TestCase

from allianceauth.utils.django import StartupCommand

MODULE_PATH = "allianceauth.utils.django"


class TestStartupCommand(TestCase):
    def test_should_detect_management_command(self):
        # when
        with patch(MODULE_PATH + ".sys") as m:
            m.argv = ["manage.py", "check"]
            info = StartupCommand()
        # then
        self.assertTrue(info.is_management_command)

    def test_should_detect_not_a_management_command(self):
        # when
        with patch(MODULE_PATH + ".sys") as m:
            m.argv = ['/home/python/allianceauth-dev/venv/bin/gunicorn', 'myauth.wsgi']
            info = StartupCommand()
        # then
        self.assertFalse(info.is_management_command)
