from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DiscourseServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.discourse'
    label = 'discourse'
    verbose_name = _('Discourse Service')
