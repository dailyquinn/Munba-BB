"""
Alliance Auth Evecharacter API
"""

from typing import Optional

from django.contrib.auth.models import User

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter
from allianceauth.framework.api.user import get_sentinel_user


def get_main_character_from_evecharacter(
    character: EveCharacter,
) -> Optional[EveCharacter]:
    """
    Get the main character for a given EveCharacter or None when no main character is set

    :param character:
    :type character:
    :return:
    :rtype:
    """

    try:
        userprofile = character.character_ownership.user.profile
    except (
        AttributeError,
        EveCharacter.character_ownership.RelatedObjectDoesNotExist,
        CharacterOwnership.user.RelatedObjectDoesNotExist,
    ):
        return None

    return userprofile.main_character


def get_user_from_evecharacter(character: EveCharacter) -> User:
    """
    Get the user for an EveCharacter or the sentinel user when no user is found

    :param character:
    :type character:
    :return:
    :rtype:
    """

    try:
        userprofile = character.character_ownership.user.profile
    except (
        AttributeError,
        EveCharacter.character_ownership.RelatedObjectDoesNotExist,
        CharacterOwnership.user.RelatedObjectDoesNotExist,
    ):
        return get_sentinel_user()

    return userprofile.user
