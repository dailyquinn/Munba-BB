from random import random
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


def random_default() -> float:
    return random()


class CronOffset(SingletonModel):

    minute = models.FloatField(_("Minute Offset"), default=random_default)
    hour = models.FloatField(_("Hour Offset"), default=random_default)
    day_of_month = models.FloatField(_("Day of Month Offset"), default=random_default)
    month_of_year = models.FloatField(_("Month of Year Offset"), default=random_default)
    day_of_week = models.FloatField(_("Day of Week Offset"), default=random_default)

    def __str__(self) -> str:
        return "Cron Offsets"

    class Meta:
        verbose_name = "Cron Offsets"
