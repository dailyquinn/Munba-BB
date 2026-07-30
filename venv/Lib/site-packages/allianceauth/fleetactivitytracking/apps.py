from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FatConfig(AppConfig):
    name = 'allianceauth.fleetactivitytracking'
    label = 'fleetactivitytracking'
    verbose_name = _('Fleet Activity Tracking')
