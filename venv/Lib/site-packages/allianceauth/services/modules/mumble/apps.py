from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MumbleServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.mumble'
    label = 'mumble'
    verbose_name = _('Mumble Service')
