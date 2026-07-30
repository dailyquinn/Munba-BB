from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServicesConfig(AppConfig):
    name = 'allianceauth.services'
    label = 'services'
    verbose_name = _('Services')

    def ready(self):
        from . import signals
