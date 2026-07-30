from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DiscordServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.discord'
    label = 'discord'
    verbose_name = _('Discord Service')
