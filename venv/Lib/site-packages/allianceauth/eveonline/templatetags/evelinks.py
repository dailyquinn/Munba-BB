# This module defines template tags for evelinks URLs and eve image URLs
#
# Many tags will work both with their respective eveonline object
# and their respective eve entity ID
#
# Example:
# character URL on evewho: {{ my_character|evewho_character_url}}
# character URL on evewho: {{ 1456384556|evewho_character_url}}
#
# For more examples see examples.html
#
# To add templatetags for additional providers just add the respective
# template functions and let them call the generic functions

from django import template

from ..models import EveCharacter, EveCorporationInfo, EveAllianceInfo
from ..evelinks import eveimageserver, evewho, dotlan, zkillboard

register = template.Library()

_DEFAULT_IMAGE_SIZE = 32


# generic functions

def _generic_character_url(
    provider: object,
    obj_prop: str,
    eve_obj: EveCharacter
) -> str:
    """returns character URL for given provider and object"""
    my_func = getattr(provider, 'character_url')
    if isinstance(eve_obj, EveCharacter):
        return my_func(getattr(eve_obj, obj_prop))

    elif eve_obj is None:
        return ''

    else:
        return my_func(eve_obj)


def _generic_corporation_url(
    provider: object,
    obj_prop: str,
    eve_obj: object
) -> str:
    """returns corporation URL for given provider and object"""
    my_func = getattr(provider, 'corporation_url')
    if isinstance(eve_obj, (EveCharacter, EveCorporationInfo)):
        return my_func(getattr(eve_obj, obj_prop))

    elif eve_obj is None:
        return ''

    else:
        return my_func(eve_obj)


def _generic_alliance_url(
    provider: object,
    obj_prop: str,
    eve_obj: object
) -> str:
    """returns alliance URL for given provider and object"""
    my_func = getattr(provider, 'alliance_url')

    if isinstance(eve_obj, EveCharacter):
        if eve_obj.alliance_id:
            return my_func(getattr(eve_obj, obj_prop))
        else:
            return ''

    elif isinstance(eve_obj, EveAllianceInfo):
        return my_func(getattr(eve_obj, obj_prop))

    elif eve_obj is None:
        return ''

    else:
        return my_func(eve_obj)


def _generic_evelinks_url(
    provider: object,
    provider_func: str,
    eve_obj: object
) -> str:
    """returns evelinks URL for given provider, function and object"""
    my_func = getattr(provider, provider_func)
    if eve_obj is None:
        return ''

    else:
        return my_func(eve_obj)


# evewho

@register.filter
def evewho_character_url(eve_obj: EveCharacter) -> str:
    """generates an evewho URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_character_url(evewho, 'character_id', eve_obj)


@register.filter
def evewho_corporation_url(eve_obj: object) -> str:
    """generates an evewho URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_corporation_url(evewho, 'corporation_id', eve_obj)


@register.filter
def evewho_alliance_url(eve_obj: object) -> str:
    """generates an evewho URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_alliance_url(evewho, 'alliance_id', eve_obj)


# dotlan

@register.filter
def dotlan_corporation_url(eve_obj: object) -> str:
    """generates a dotlan URL for the given object
    Works with allianceauth.eveonline objects and eve entity names
    Returns URL or empty string
    """
    return _generic_corporation_url(dotlan, 'corporation_name', eve_obj)


@register.filter
def dotlan_alliance_url(eve_obj: object) -> str:
    """generates a dotlan URL for the given object
    Works with allianceauth.eveonline objects and eve entity names
    Returns URL or empty string
    """
    return _generic_alliance_url(dotlan, 'alliance_name', eve_obj)


@register.filter
def dotlan_region_url(eve_obj: object) -> str:
    """generates a dotlan URL for the given object
    Works with eve entity names
    Returns URL or empty string
    """
    return _generic_evelinks_url(dotlan, 'region_url', eve_obj)


@register.filter
def dotlan_solar_system_url(eve_obj: object) -> str:
    """generates a dotlan URL for the given object
    Works with eve entity names
    Returns URL or empty string
    """
    return _generic_evelinks_url(dotlan, 'solar_system_url', eve_obj)


# zkillboard

@register.filter
def zkillboard_character_url(eve_obj: EveCharacter) -> str:
    """generates a zkillboard URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_character_url(zkillboard, 'character_id', eve_obj)


@register.filter
def zkillboard_corporation_url(eve_obj: object) -> str:
    """generates a zkillboard URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_corporation_url(zkillboard, 'corporation_id', eve_obj)


@register.filter
def zkillboard_alliance_url(eve_obj: object) -> str:
    """generates a zkillboard URL for the given object
    Works with allianceauth.eveonline objects and eve entity IDs
    Returns URL or empty string
    """
    return _generic_alliance_url(zkillboard, 'alliance_id', eve_obj)


@register.filter
def zkillboard_region_url(eve_obj: object) -> str:
    """generates a zkillboard URL for the given object
    Works with eve entity IDs
    Returns URL or empty string
    """
    return _generic_evelinks_url(zkillboard, 'region_url', eve_obj)


@register.filter
def zkillboard_solar_system_url(eve_obj: object) -> str:
    """generates zkillboard URL for the given object
    Works with eve entity IDs
    Returns URL or empty string
    """
    return _generic_evelinks_url(zkillboard, 'solar_system_url', eve_obj)


# image urls

@register.filter
def character_portrait_url(
    eve_obj: object,
    size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """generates an image URL for the given object
    Works with EveCharacter objects or character IDs
    Returns URL or empty string
    """
    if isinstance(eve_obj, EveCharacter):
        return eve_obj.portrait_url(size)

    elif eve_obj is None:
        return ''

    else:
        try:
            return EveCharacter.generic_portrait_url(eve_obj, size)
        except ValueError:
            return ''


@register.filter
def corporation_logo_url(
    eve_obj: object,
    size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """generates image URL for the given object
    Works with EveCharacter, EveCorporationInfo objects or corporation IDs
    Returns URL or empty string
    """
    if isinstance(eve_obj, EveCorporationInfo):
        return eve_obj.logo_url(size)

    elif isinstance(eve_obj, EveCharacter):
        return eve_obj.corporation_logo_url(size)

    elif eve_obj is None:
        return ''

    else:
        try:
            return EveCorporationInfo.generic_logo_url(eve_obj, size)
        except ValueError:
            return ''


@register.filter
def alliance_logo_url(
    eve_obj: object,
    size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """generates image URL for the given object
    Works with EveCharacter, EveAllianceInfo objects or alliance IDs
    Returns URL or empty string
    """
    if isinstance(eve_obj, EveAllianceInfo):
        return eve_obj.logo_url(size)

    elif isinstance(eve_obj, EveCharacter):
        return eve_obj.alliance_logo_url(size)

    elif eve_obj is None:
        return ''

    else:
        try:
            return EveAllianceInfo.generic_logo_url(eve_obj, size)
        except ValueError:
            return ''


@register.filter
def type_icon_url(
    type_id: int,
    size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """generates a icon image URL for the given type ID
    Returns URL or empty string
    """
    try:
        return eveimageserver.type_icon_url(type_id, size)
    except ValueError:
        return ''


@register.filter
def type_render_url(
    type_id: int,
    size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """generates a render image URL for the given type ID
    Returns URL or empty string
    """
    try:
        return eveimageserver.type_render_url(type_id, size)
    except ValueError:
        return ''
