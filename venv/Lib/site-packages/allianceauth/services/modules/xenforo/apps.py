from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class XenforoServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.xenforo'
    label = 'xenforo'
    verbose_name = _('Xenforo Service')
