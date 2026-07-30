from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Ips4ServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.ips4'
    label = 'ips4'
    verbose_name = _('IPS4 Service')
