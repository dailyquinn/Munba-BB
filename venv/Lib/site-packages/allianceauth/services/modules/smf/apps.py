from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SmfServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.smf'
    label = 'smf'
    verbose_name = _('SMF Service')
