from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Teamspeak3ServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.teamspeak3'
    label = 'teamspeak3'
    verbose_name = _('TeamSpeak 3 Service')

    def ready(self):
        from . import signals
