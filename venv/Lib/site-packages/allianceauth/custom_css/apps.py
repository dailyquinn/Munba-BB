"""
Django app configuration for custom_css
"""

# Django
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CustomCSSConfig(AppConfig):
    name = "allianceauth.custom_css"
    label = "custom_css"
    verbose_name = _("Custom CSS")
