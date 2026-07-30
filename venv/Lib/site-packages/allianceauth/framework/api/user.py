"""
Alliance Auth User API
"""

from typing import Optional

from django.contrib.auth.models import User

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter


def get_all_characters_from_user(user: User, main_first: bool = False) -> list:
    """
    Get all characters from a user
    This function retrieves all characters associated with a given user, optionally ordering them
    with the main character first.
    If the user is None, an empty list is returned.

    :param user: The user whose characters are to be retrieved
    :type user: User
    :param main_first: If True, the main character will be listed first
    :type main_first: bool
    :return: A list of EveCharacter objects associated with the user
    :rtype: list[EveCharacter]
    """

    if user is None:
        return []

    try:
        if main_first:
            characters = [
                char.character
                for char in CharacterOwnership.objects.filter(user=user).order_by(
                    "-character__userprofile", "character__character_name"
                )
            ]
        else:
            characters = [
                char.character
                for char in CharacterOwnership.objects.filter(user=user).order_by(
                    "character__character_name"
                )
            ]
    except AttributeError:
        return []

    return characters


def get_main_character_from_user(user: User) -> Optional[EveCharacter]:
    """
    Get the main character from a user

    :param user:
    :type user:
    :return:
    :rtype:
    """

    if user is None:
        return None

    try:
        main_character = user.profile.main_character
    except AttributeError:
        return None

    return main_character


def get_main_character_name_from_user(user: User) -> str:
    """
    Get the main character name from a user

    :param user:
    :type user:
    :return:
    :rtype:
    """

    if user is None:
        sentinel_user = get_sentinel_user()

        return sentinel_user.username

    main_character = get_main_character_from_user(user=user)

    try:
        username = main_character.character_name
    except AttributeError:
        return str(user)

    return username


def get_sentinel_user() -> User:
    """
    Get the sentinel user or create one

    :return:
    """

    return User.objects.get_or_create(username="deleted")[0]
