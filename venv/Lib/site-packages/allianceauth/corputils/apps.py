from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CorpUtilsConfig(AppConfig):
    name = 'allianceauth.corputils'
    label = 'corputils'
    verbose_name = _('Corporation Stats')
