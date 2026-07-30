from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SRPConfig(AppConfig):
    name = 'allianceauth.srp'
    label = 'srp'
    verbose_name = _('Ship Replacement')
