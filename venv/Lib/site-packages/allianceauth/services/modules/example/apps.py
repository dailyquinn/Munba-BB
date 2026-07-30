from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExampleServiceConfig(AppConfig):
    name = 'allianceauth.services.modules.example'
    label = 'example_service'
    verbose_name = _('Example Service')
