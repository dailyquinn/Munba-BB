"""
Crontab App Config
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CrontabConfig(AppConfig):
    """
    Crontab App Config
    """

    name = "allianceauth.crontab"
    label = "crontab"
    verbose_name = _("Crontab")
