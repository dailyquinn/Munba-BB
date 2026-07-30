from . import (
    _ESI_CATEGORY_ALLIANCE,
    _ESI_CATEGORY_CHARACTER,
    _ESI_CATEGORY_CORPORATION,
    _ESI_CATEGORY_INVENTORYTYPE
)


_EVE_IMAGE_SERVER_URL = 'https://images.evetech.net'
_DEFAULT_IMAGE_SIZE = 32


def _eve_entity_image_url(
    category: str,
    entity_id: int,
    size: int = 32,
    variant: str = None,
    tenant: str = None,
) -> str:
    """returns image URL for an Eve Online ID.
    Supported categories: alliance, corporation, character, inventory_type

    Arguments:
    - category: category of the ID, see ESI category constants
    - entity_id: Eve ID of the entity
    - size: (optional) render size of the image.must be between 32 (default) and 1024
    - variant: (optional) image variant for category. currently not relevant.
    - tenant: (optional) Eve Server, either `tranquility`(default) or `singularity`

    Returns:
    - URL string for the requested image on the Eve image server

    Exceptions:
    - Throws ValueError on invalid input
    """

    # input validations
    categories = {
        _ESI_CATEGORY_ALLIANCE: {
            'endpoint': 'alliances',
            'variants': ['logo']
        },
        _ESI_CATEGORY_CORPORATION: {
            'endpoint': 'corporations',
            'variants': ['logo']
        },
        _ESI_CATEGORY_CHARACTER: {
            'endpoint': 'characters',
            'variants': ['portrait']
        },
        _ESI_CATEGORY_INVENTORYTYPE: {
            'endpoint': 'types',
            'variants': ['icon', 'render']
        }
    }
    tenants = ['tranquility', 'singularity']

    if not entity_id:
        raise ValueError(f'Invalid entity_id: {entity_id}')
    else:
        entity_id = int(entity_id)

    if not size or size < 32 or size > 1024 or (size & (size - 1) != 0):
        raise ValueError(f'Invalid size: {size}')

    if category not in categories:
        raise ValueError(f'Invalid category {category}')
    else:
        endpoint = categories[category]['endpoint']

    if variant:
        if variant not in categories[category]['variants']:
            raise ValueError('Invalid variant {} for category {}'.format(
                variant,
                category
            ))
    else:
        variant = categories[category]['variants'][0]

    if tenant and tenant not in tenants:
        raise ValueError(f'Invalid tenant {tenant}')

    # compose result URL
    result = '{}/{}/{}/{}?size={}'.format(
        _EVE_IMAGE_SERVER_URL,
        endpoint,
        entity_id,
        variant,
        size
    )
    if tenant:
        result += f'&tenant={tenant}'

    return result


def alliance_logo_url(alliance_id: int, size: int = _DEFAULT_IMAGE_SIZE) -> str:
    """image URL for the given alliance ID"""
    return _eve_entity_image_url(_ESI_CATEGORY_ALLIANCE, alliance_id, size)


def corporation_logo_url(
    corporation_id: int, size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """image URL for the given corporation ID"""
    return _eve_entity_image_url(
        _ESI_CATEGORY_CORPORATION, corporation_id, size
    )


def character_portrait_url(
    character_id: int, size: int = _DEFAULT_IMAGE_SIZE
) -> str:
    """image URL for the given character ID"""
    return _eve_entity_image_url(_ESI_CATEGORY_CHARACTER, character_id, size)


def type_icon_url(type_id: int, size: int = _DEFAULT_IMAGE_SIZE) -> str:
    """icon image URL for the given type ID"""
    return _eve_entity_image_url(
        _ESI_CATEGORY_INVENTORYTYPE, type_id, size, variant='icon'
    )


def type_render_url(type_id: int, size: int = _DEFAULT_IMAGE_SIZE) -> str:
    """render image URL for the given type ID"""
    return _eve_entity_image_url(
        _ESI_CATEGORY_INVENTORYTYPE, type_id, size, variant='render'
    )
