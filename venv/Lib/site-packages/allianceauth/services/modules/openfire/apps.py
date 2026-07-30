from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OpenfireServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.openfire'
    label = 'openfire'
    verbose_name = _('Openfire Service')
