"""
Framework App Config
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FrameworkConfig(AppConfig):
    """
    Framework App Config
    """

    name = "allianceauth.framework"
    label = "framework"
    verbose_name = _("Framework")
