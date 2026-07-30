from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Phpbb3ServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.phpbb3'
    label = 'phpbb3'
    verbose_name = _('phpBB3 Service')
