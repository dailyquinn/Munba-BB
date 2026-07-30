from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EveAutogroupsConfig(AppConfig):
    name = 'allianceauth.eveonline.autogroups'
    label = 'eve_autogroups'
    verbose_name = _('EVE Online Autogroups')

    def ready(self):
        import allianceauth.eveonline.autogroups.signals
