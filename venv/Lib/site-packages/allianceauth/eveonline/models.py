import logging
from typing import ClassVar, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from esi.models import Token

from allianceauth.notifications import notify

from . import providers
from .evelinks import eveimageserver
from .managers import (
    EveAllianceManager,
    EveAllianceProviderManager,
    EveCharacterManager,
    EveCharacterProviderManager,
    EveCorporationManager,
    EveCorporationProviderManager,
)

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE_SIZE = 32
DOOMHEIM_CORPORATION_ID = 1000001


class EveFactionInfo(models.Model):
    """A faction in Eve Online."""

    faction_id = models.PositiveIntegerField(unique=True, db_index=True)
    faction_name = models.CharField(max_length=254, unique=True)

    provider = providers.provider

    def __str__(self):
        return self.faction_name

    @staticmethod
    def generic_logo_url(
        faction_id: int, size: int = _DEFAULT_IMAGE_SIZE
    ) -> str:
        """image URL for the given faction ID"""
        return eveimageserver.corporation_logo_url(faction_id, size)

    def logo_url(self, size: int = _DEFAULT_IMAGE_SIZE) -> str:
        """image URL of this faction"""
        return self.generic_logo_url(self.faction_id, size)

    @property
    def logo_url_32(self) -> str:
        """image URL for this faction"""
        return self.logo_url(32)

    @property
    def logo_url_64(self) -> str:
        """image URL for this faction"""
        return self.logo_url(64)

    @property
    def logo_url_128(self) -> str:
        """image URL for this faction"""
        return self.logo_url(128)

    @property
    def logo_url_256(self) -> str:
        """image URL for this faction"""
        return self.logo_url(256)


class EveAllianceInfo(models.Model):
    """An alliance in Eve Online."""

    alliance_id = models.PositiveIntegerField(unique=True)
    alliance_name = models.CharField(max_length=254, db_index=True)
    alliance_ticker = models.CharField(max_length=254)
    executor_corp_id = models.PositiveIntegerField()

    objects: ClassVar[EveAllianceManager] = EveAllianceManager()
    provider: ClassVar[EveAllianceProviderManager] = EveAllianceProviderManager()

    class Meta:
        indexes = [models.Index(fields=['executor_corp_id',])]

    def populate_alliance(self):
        alliance = self.provider.get_alliance(self.alliance_id)
        for corp_id in alliance.corp_ids:
            if not EveCorporationInfo.objects.filter(corporation_id=corp_id).exists():
                EveCorporationInfo.objects.create_corporation(corp_id)
        EveCorporationInfo.objects.filter(corporation_id__in=alliance.corp_ids).update(
            alliance=self
        )
        EveCorporationInfo.objects.filter(alliance=self).exclude(
            corporation_id__in=alliance.corp_ids
        ).update(alliance=None)

    def update_alliance(self, alliance: providers.Alliance = None):
        if alliance is None:
            alliance = self.provider.get_alliance(self.alliance_id)
        self.executor_corp_id = alliance.executor_corp_id
        self.save()
        return self

    def __str__(self):
        return self.alliance_name

    @staticmethod
    def generic_logo_url(
        alliance_id: int, size: int = _DEFAULT_IMAGE_SIZE
    ) -> str:
        """image URL for the given alliance ID"""
        return eveimageserver.alliance_logo_url(alliance_id, size)

    def logo_url(self, size: int = _DEFAULT_IMAGE_SIZE) -> str:
        """image URL of this alliance"""
        return self.generic_logo_url(self.alliance_id, size)

    @property
    def logo_url_32(self) -> str:
        """image URL for this alliance"""
        return self.logo_url(32)

    @property
    def logo_url_64(self) -> str:
        """image URL for this alliance"""
        return self.logo_url(64)

    @property
    def logo_url_128(self) -> str:
        """image URL for this alliance"""
        return self.logo_url(128)

    @property
    def logo_url_256(self) -> str:
        """image URL for this alliance"""
        return self.logo_url(256)


class EveCorporationInfo(models.Model):
    """A corporation in Eve Online."""

    corporation_id = models.PositiveIntegerField(unique=True)
    corporation_name = models.CharField(max_length=254, db_index=True)
    corporation_ticker = models.CharField(max_length=254)
    member_count = models.IntegerField()
    ceo_id = models.PositiveIntegerField(blank=True, null=True, default=None)
    alliance = models.ForeignKey(
        EveAllianceInfo, blank=True, null=True, on_delete=models.SET_NULL
    )

    objects: ClassVar[EveCorporationManager] = EveCorporationManager()
    provider = EveCorporationProviderManager()

    class Meta:
        indexes = [models.Index(fields=['ceo_id',]),]

    def update_corporation(self, corp: providers.Corporation = None):
        if corp is None:
            corp = self.provider.get_corporation(self.corporation_id)
        self.member_count = corp.members
        self.ceo_id = corp.ceo_id
        try:
            self.alliance = EveAllianceInfo.objects.get(alliance_id=corp.alliance_id)
        except EveAllianceInfo.DoesNotExist:
            self.alliance = None
        self.save()
        return self

    def __str__(self):
        return self.corporation_name

    @staticmethod
    def generic_logo_url(
        corporation_id: int, size: int = _DEFAULT_IMAGE_SIZE
    ) -> str:
        """image URL for the given corporation ID"""
        return eveimageserver.corporation_logo_url(corporation_id, size)

    def logo_url(self, size: int = _DEFAULT_IMAGE_SIZE) -> str:
        """image URL for this corporation"""
        return self.generic_logo_url(self.corporation_id, size)

    @property
    def logo_url_32(self) -> str:
        """image URL for this corporation"""
        return self.logo_url(32)

    @property
    def logo_url_64(self) -> str:
        """image URL for this corporation"""
        return self.logo_url(64)

    @property
    def logo_url_128(self) -> str:
        """image URL for this corporation"""
        return self.logo_url(128)

    @property
    def logo_url_256(self) -> str:
        """image URL for this corporation"""
        return self.logo_url(256)


class EveCharacter(models.Model):
    """A character in Eve Online."""

    character_id = models.PositiveIntegerField(unique=True)
    character_name = models.CharField(max_length=254, db_index=True)
    corporation_id = models.PositiveIntegerField()
    corporation_name = models.CharField(max_length=254)
    corporation_ticker = models.CharField(max_length=5)
    alliance_id = models.PositiveIntegerField(blank=True, null=True, default=None)
    alliance_name = models.CharField(max_length=254, blank=True, null=True, default='')
    alliance_ticker = models.CharField(max_length=5, blank=True, null=True, default='')
    faction_id = models.PositiveIntegerField(blank=True, null=True, default=None)
    faction_name = models.CharField(max_length=254, blank=True, null=True, default='')

    objects: ClassVar[EveCharacterManager] = EveCharacterManager()
    provider = EveCharacterProviderManager()

    class Meta:
        indexes = [
            models.Index(fields=['corporation_id',]),
            models.Index(fields=['alliance_id',]),
            models.Index(fields=['corporation_name',]),
            models.Index(fields=['alliance_name',]),
            models.Index(fields=['faction_id',]),
        ]

    def __str__(self):
        return self.character_name

    @property
    def is_biomassed(self) -> bool:
        """Whether this character is dead or not."""
        return self.corporation_id == DOOMHEIM_CORPORATION_ID

    @property
    def alliance(self) -> Union[EveAllianceInfo, None]:
        """
        Pseudo foreign key from alliance_id to EveAllianceInfo
        :raises: EveAllianceInfo.DoesNotExist
        :return: EveAllianceInfo or None
        """
        if self.alliance_id is None:
            return None
        return EveAllianceInfo.objects.get(alliance_id=self.alliance_id)

    @property
    def corporation(self) -> EveCorporationInfo:
        """
        Pseudo foreign key from corporation_id to EveCorporationInfo
        :raises: EveCorporationInfo.DoesNotExist
        :return: EveCorporationInfo
        """
        return EveCorporationInfo.objects.get(corporation_id=self.corporation_id)

    @property
    def faction(self) -> Union[EveFactionInfo, None]:
        """
        Pseudo foreign key from faction_id to EveFactionInfo
        :raises: EveFactionInfo.DoesNotExist
        :return: EveFactionInfo
        """
        if self.faction_id is None:
            return None
        return EveFactionInfo.objects.get(faction_id=self.faction_id)

    def update_character(self, character: providers.Character = None):
        if character is None:
            character = self.provider.get_character(self.character_id)
        self.character_name = character.name
        self.corporation_id = character.corp.id
        self.corporation_name = character.corp.name
        self.corporation_ticker = character.corp.ticker
        self.alliance_id = character.alliance.id
        self.alliance_name = character.alliance.name
        self.alliance_ticker = getattr(character.alliance, 'ticker', None)
        self.faction_id = character.faction.id
        self.faction_name = character.faction.name
        self.save()
        if self.is_biomassed:
            self._remove_tokens_of_biomassed_character()
        return self

    def _remove_tokens_of_biomassed_character(self) -> None:
        """Remove tokens of this biomassed character."""
        try:
            user = self.character_ownership.user
        except ObjectDoesNotExist:
            return
        tokens_to_delete = Token.objects.filter(character_id=self.character_id)
        tokens_count = tokens_to_delete.count()
        if not tokens_count:
            return
        tokens_to_delete.delete()
        logger.info(
            "%d tokens from user %s for biomassed character %s [id:%s] deleted.",
            tokens_count,
            user,
            self,
            self.character_id,
        )
        notify(
            user=user,
            title=f"Character {self} biomassed",
            message=(
                f"Your former character {self} has been biomassed "
                "and has been removed from the list of your alts."
            )
        )

    @staticmethod
    def generic_portrait_url(
        character_id: int, size: int = _DEFAULT_IMAGE_SIZE
    ) -> str:
        """image URL for the given character ID"""
        return eveimageserver.character_portrait_url(character_id, size)

    def portrait_url(self, size=_DEFAULT_IMAGE_SIZE) -> str:
        """image URL for this character"""
        return self.generic_portrait_url(self.character_id, size)

    @property
    def portrait_url_32(self) -> str:
        """image URL for this character"""
        return self.portrait_url(32)

    @property
    def portrait_url_64(self) -> str:
        """image URL for this character"""
        return self.portrait_url(64)

    @property
    def portrait_url_128(self) -> str:
        """image URL for this character"""
        return self.portrait_url(128)

    @property
    def portrait_url_256(self) -> str:
        """image URL for this character"""
        return self.portrait_url(256)

    def corporation_logo_url(self, size=_DEFAULT_IMAGE_SIZE) -> str:
        """image URL for corporation of this character"""
        return EveCorporationInfo.generic_logo_url(self.corporation_id, size)

    @property
    def corporation_logo_url_32(self) -> str:
        """image URL for corporation of this character"""
        return self.corporation_logo_url(32)

    @property
    def corporation_logo_url_64(self) -> str:
        """image URL for corporation of this character"""
        return self.corporation_logo_url(64)

    @property
    def corporation_logo_url_128(self) -> str:
        """image URL for corporation of this character"""
        return self.corporation_logo_url(128)

    @property
    def corporation_logo_url_256(self) -> str:
        """image URL for corporation of this character"""
        return self.corporation_logo_url(256)

    def alliance_logo_url(self, size=_DEFAULT_IMAGE_SIZE) -> str:
        """image URL for alliance of this character or empty string"""
        if self.alliance_id:
            return EveAllianceInfo.generic_logo_url(self.alliance_id, size)
        else:
            return ''

    @property
    def alliance_logo_url_32(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.alliance_logo_url(32)

    @property
    def alliance_logo_url_64(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.alliance_logo_url(64)

    @property
    def alliance_logo_url_128(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.alliance_logo_url(128)

    @property
    def alliance_logo_url_256(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.alliance_logo_url(256)

    def faction_logo_url(self, size=_DEFAULT_IMAGE_SIZE) -> str:
        """image URL for alliance of this character or empty string"""
        if self.faction_id:
            return EveFactionInfo.generic_logo_url(self.faction_id, size)
        else:
            return ''

    @property
    def faction_logo_url_32(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.faction_logo_url(32)

    @property
    def faction_logo_url_64(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.faction_logo_url(64)

    @property
    def faction_logo_url_128(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.faction_logo_url(128)

    @property
    def faction_logo_url_256(self) -> str:
        """image URL for alliance of this character or empty string"""
        return self.faction_logo_url(256)
