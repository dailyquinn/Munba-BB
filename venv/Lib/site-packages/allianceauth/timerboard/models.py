from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from allianceauth.eveonline.models import EveCharacter
from allianceauth.eveonline.models import EveCorporationInfo


class Timer(models.Model):
    class Objective(models.TextChoices):
        """
        Choices for Objective Type
        """

        FRIENDLY = "Friendly", _("Friendly")
        HOSTILE = "Hostile", _("Hostile")
        NEUTRAL = "Neutral", _("Neutral")

    class Structure(models.TextChoices):
        """
        Choices for Structure Type
        """

        OTHER = "Other", _("Other")

        ASTRAHUS = "Astrahus", _("Astrahus")
        ATHANOR = "Athanor", _("Athanor")
        AZBEL = "Azbel", _("Azbel")
        PHAROLUX = "Pharolux Cyno Beacon", _("Cyno Beacon")
        TENEBREX = "Tenebrex Cyno Jammer", _("Cyno Jammer")
        FORTIZAR = "Fortizar", _("Fortizar")
        ANSIBLEX = "Ansiblex Jump Gate", _("Jump Bridge")
        KEEPSTAR = "Keepstar", _("Keepstar")
        MERCDEN = "Mercenary Den", _("Mercenary Den")
        METENOX = "Metenox Moon Drill", _("Moon Drill")
        MOONPOP = "Moon Mining Cycle", _("Moon Mining Cycle")
        POCO = "POCO", _("POCO")
        POSS = "POS[S]", _("POS [S]")
        POSM = "POS[M]", _("POS [M]")
        POSL = "POS[L]", _("POS [L]")
        RAITARU = "Raitaru", _("Raitaru")
        ORBITALSKYHOOK = "Orbital Skyhook", _("Skyhook")
        SOTIYO = "Sotiyo", _("Sotiyo")
        IHUB = "I-HUB", _("Sovereignty Hub")
        TATARA = "Tatara", _("Tatara")

    class TimerType(models.TextChoices):
        """
        Choices for Timer Type
        """

        UNSPECIFIED = "UNSPECIFIED", _("Not Specified")
        SHIELD = "SHIELD", _("Shield")
        ARMOR = "ARMOR", _("Armor")
        HULL = "HULL", _("Hull")
        FINAL = "FINAL", _("Final")
        ANCHORING = "ANCHORING", _("Anchoring")
        UNANCHORING = "UNANCHORING", _("Unanchoring")
        ABANDONED = "ABANDONED", _("Abandoned")
        THEFT = "THEFT", _("Theft")

    details = models.CharField(max_length=254, default="")
    system = models.CharField(max_length=254, default="")
    planet_moon = models.CharField(max_length=254, blank=True, default="")
    structure = models.CharField(max_length=254,choices=Structure.choices,default=Structure.OTHER)
    timer_type = models.CharField(max_length=254,choices=TimerType.choices,default=TimerType.UNSPECIFIED)
    objective = models.CharField(max_length=254, choices=Objective.choices, default=Objective.NEUTRAL)
    eve_time = models.DateTimeField()
    important = models.BooleanField(default=False)
    eve_character = models.ForeignKey(EveCharacter, null=True, on_delete=models.SET_NULL)
    eve_corp = models.ForeignKey(EveCorporationInfo, on_delete=models.CASCADE)
    corp_timer = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return str(self.system) + ' ' + str(self.details)

    class Meta:
        ordering = ['eve_time']
