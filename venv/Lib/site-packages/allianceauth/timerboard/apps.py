from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TimerBoardConfig(AppConfig):
    name = 'allianceauth.timerboard'
    label = 'timerboard'
    verbose_name = _('Structure Timers')
