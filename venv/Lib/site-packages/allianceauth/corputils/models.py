import logging
import os
from typing import ClassVar

from allianceauth.authentication.models import CharacterOwnership, UserProfile
from bravado.exception import HTTPForbidden
from django.db import models
from esi.errors import TokenError
from esi.models import Token
from allianceauth.eveonline.models import EveCorporationInfo, EveCharacter, EveAllianceInfo
from allianceauth.notifications import notify

from allianceauth.corputils.managers import CorpStatsManager

SWAGGER_SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.json')
"""
Swagger spec operations:

Character
get_characters_character_id
get_corporations_corporation_id_members
Universe
post_universe_names
"""


logger = logging.getLogger(__name__)


class CorpStats(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    corp = models.OneToOneField(EveCorporationInfo, on_delete=models.CASCADE)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ('view_corp_corpstats', 'Can view corp stats of their corporation.'),
            ('view_alliance_corpstats', 'Can view corp stats of members of their alliance.'),
            ('view_state_corpstats', 'Can view corp stats of members of their auth state.'),
        )
        verbose_name = "corp stats"
        verbose_name_plural = "corp stats"

    objects: ClassVar[CorpStatsManager] = CorpStatsManager()

    def __str__(self) -> str:
        return f"{self.__class__.__name__} for {self.corp}"

    def update(self):
        try:
            c = self.token.get_esi_client(spec_file=SWAGGER_SPEC_PATH)
            assert c.Character.get_characters_character_id(character_id=self.token.character_id).result()['corporation_id'] == int(self.corp.corporation_id)
            member_ids = c.Corporation.get_corporations_corporation_id_members(
                corporation_id=self.corp.corporation_id).result()

            # requesting too many ids per call results in a HTTP400
            # the swagger spec doesn't have a maxItems count
            # manual testing says we can do over 350, but let's not risk it
            member_id_chunks = [member_ids[i:i + 255] for i in range(0, len(member_ids), 255)]
            member_name_chunks = [c.Universe.post_universe_names(ids=id_chunk).result() for id_chunk in member_id_chunks]
            member_list = {}
            for name_chunk in member_name_chunks:
                member_list.update({m['id']: m['name'] for m in name_chunk})

            # bulk create new member models
            missing_members = [m_id for m_id in member_ids if not CorpMember.objects.filter(corpstats=self, character_id=m_id).exists()]
            CorpMember.objects.bulk_create(
                [CorpMember(character_id=m_id, character_name=member_list[m_id], corpstats=self) for m_id in missing_members])

            # purge old members
            self.members.exclude(character_id__in=member_ids).delete()

            # update the timer
            self.save()

        except TokenError as e:
            logger.warning(f"{self} failed to update: {e}")
            if self.token.user:
                notify(
                    self.token.user, "%s failed to update with your ESI token." % self,
                    message="Your token has expired or is no longer valid. Please add a new one to create a new CorpStats.",
                    level="error")
            self.delete()
        except HTTPForbidden as e:
            logger.warning(f"{self} failed to update: {e}")
            if self.token.user:
                notify(self.token.user, "%s failed to update with your ESI token." % self, message=f"{e.status_code}: {e.message}", level="error")
            self.delete()
        except AssertionError:
            logger.warning("%s token character no longer in corp." % self)
            if self.token.user:
                notify(
                    self.token.user, "%s cannot update with your ESI token." % self,
                    message="%s cannot update with your ESI token as you have left corp." % self, level="error")
            self.delete()

    @property
    def member_count(self):
        return self.members.count()

    @property
    def user_count(self):
        return len({m.main_character for m in self.members.all() if m.main_character})

    @property
    def registered_member_count(self):
        return len(self.registered_members)

    @property
    def registered_members(self):
        return self.members.filter(pk__in=[m.pk for m in self.members.all() if m.registered])

    @property
    def unregistered_member_count(self):
        return self.member_count - self.registered_member_count

    @property
    def unregistered_members(self):
        return self.members.filter(pk__in=[m.pk for m in self.members.all() if not m.registered])

    @property
    def main_count(self):
        return len(self.mains)

    @property
    def mains(self):
        return self.members.filter(pk__in=[m.pk for m in self.members.all() if m.main_character and int(m.main_character.character_id) == int(m.character_id)])

    def visible_to(self, user):
        return CorpStats.objects.filter(pk=self.pk).visible_to(user).exists()

    def can_update(self, user):
        return self.token.user == user or self.visible_to(user)

    def corp_logo(self, size=128):
        return self.corp.logo_url(size)

    def alliance_logo(self, size=128):
        if self.corp.alliance:
            return self.corp.alliance.logo_url(size)
        else:
            return EveAllianceInfo.generic_logo_url(1, size)


class CorpMember(models.Model):
    character_id = models.PositiveIntegerField()
    character_name = models.CharField(max_length=37)
    corpstats = models.ForeignKey(CorpStats, on_delete=models.CASCADE, related_name='members')

    class Meta:
        # not making character_id unique in case a character moves between two corps while only one updates
        unique_together = ('corpstats', 'character_id')
        ordering = ['character_name']

    def __str__(self):
        return self.character_name

    @property
    def character(self):
        try:
            return EveCharacter.objects.get(character_id=self.character_id)
        except EveCharacter.DoesNotExist:
            return None

    @property
    def main_character(self):
        try:
            return self.character.character_ownership.user.profile.main_character
        except (CharacterOwnership.DoesNotExist, UserProfile.DoesNotExist, AttributeError):
            return None

    @property
    def alts(self):
        if self.main_character:
            return [co.character for co in self.main_character.character_ownership.user.character_ownerships.all()]
        else:
            return []

    @property
    def registered(self):
        return CharacterOwnership.objects.filter(character__character_id=self.character_id).exists()

    def portrait_url(self, size=32):
        return EveCharacter.generic_portrait_url(self.character_id, size)

    @property
    def portrait_url_32(self):
        return self.portrait_url(32)

    @property
    def portrait_url_64(self):
        return self.portrait_url(64)

    @property
    def portrait_url_128(self):
        return self.portrait_url(128)
