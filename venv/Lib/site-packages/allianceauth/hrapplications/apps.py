from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HRApplicationsConfig(AppConfig):
    name = 'allianceauth.hrapplications'
    label = 'hrapplications'
    verbose_name = _('HR Applications')
