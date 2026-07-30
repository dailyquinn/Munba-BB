from typing import Literal
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel
from uuid import uuid4


class AnalyticsIdentifier(SingletonModel):

    identifier = models.UUIDField(default=uuid4, editable=False)

    def __str__(self) -> Literal['Analytics Identifier']:
        return "Analytics Identifier"

    class Meta:
        verbose_name = "Analytics Identifier"


class AnalyticsTokens(models.Model):

    class Analytics_Type(models.TextChoices):
        GA_U = 'GA-U', _('Google Analytics Universal')
        GA_V4 = 'GA-V4', _('Google Analytics V4')

    name = models.CharField(max_length=254)
    type = models.CharField(max_length=254, choices=Analytics_Type.choices)
    token = models.CharField(max_length=254, blank=False)
    secret = models.CharField(max_length=254, blank=True)
    send_stats = models.BooleanField(default=False)
