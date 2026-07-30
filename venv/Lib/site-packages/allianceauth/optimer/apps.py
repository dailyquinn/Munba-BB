from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OptimerConfig(AppConfig):
    name = 'allianceauth.optimer'
    label = 'optimer'
    verbose_name = _('Fleet Operations')
