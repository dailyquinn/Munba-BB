from django.conf import settings


def _clean_setting(
    name: str,
    default_value: object,
    min_value: int = None,
    max_value: int = None,
    required_type: type = None
):
    """cleans the input for a custom setting

    Will use `default_value` if settings does not exit or has the wrong type
    or is outside define boundaries (for int only)

    Need to define `required_type` if `default_value` is `None`

    Will assume `min_value` of 0 for int (can be overriden)

    Returns cleaned value for setting
    """
    if default_value is None and not required_type:
        raise ValueError('You must specify a required_type for None defaults')

    if not required_type:
        required_type = type(default_value)

    if min_value is None and required_type == int:
        min_value = 0

    if (hasattr(settings, name)
        and isinstance(getattr(settings, name), required_type)
        and (min_value is None or getattr(settings, name) >= min_value)
        and (max_value is None or getattr(settings, name) <= max_value)
    ):
        return getattr(settings, name)
    else:
        return default_value


AUTHENTICATION_ADMIN_USERS_MAX_GROUPS = \
    _clean_setting('AUTHENTICATION_ADMIN_USERS_MAX_GROUPS', 10)

AUTHENTICATION_ADMIN_USERS_MAX_CHARS = \
    _clean_setting('AUTHENTICATION_ADMIN_USERS_MAX_CHARS', 5)
