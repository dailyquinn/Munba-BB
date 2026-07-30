"""
Template tags for language mapping
"""

from django.conf import settings
from django.template.defaulttags import register
from django.templatetags.static import static


@register.simple_tag
def get_datatable_language_code(language: str) -> str:
    """
    Get the correct language code for DataTables

    :param language: Django's language code
    :type language: str
    :return: Mapped language code
    :rtype: str
    """

    mapped_language = (
        settings.LANGUAGE_MAPPING["DataTables"].get(language)
        if language != "en"
        else ""
    )

    return mapped_language


@register.simple_tag
def get_momentjs_language_code(language: str) -> str:
    """
    Get the correct language code for Moment.JS

    :param language: Django's language code
    :type language: str
    :return: Mapped language code
    :rtype: str
    """

    mapped_language = (
        settings.LANGUAGE_MAPPING["MomentJS"].get(language) if language != "en" else ""
    )

    return mapped_language


@register.simple_tag
def get_datatables_language_static(language: str) -> str:
    """
    Get the correct language code URL for DataTables

    :param language: Django's language code
    :type language: str
    :return: Mapped language code
    :rtype: str
    """

    mapped_language = get_datatable_language_code(language)
    static_url = (
        static(
            path=f"allianceauth/libs/DataTables/Plugins/2.3.6/i18n/{mapped_language}.json"
        )
        if mapped_language
        else ""
    )

    return static_url

@register.simple_tag
def get_relative_datatables_language_path(language: str) -> str:
    """
    Get the correct language code URL for DataTables (relative path to the static folder)

    :param language: Django's language code
    :type language: str
    :return: Mapped language code
    :rtype: str
    """

    mapped_language = get_datatable_language_code(language)
    static_url = (
        f"allianceauth/libs/DataTables/Plugins/2.2.1/i18n/{mapped_language}.json"
        if mapped_language
        else ""
    )

    return static_url


@register.simple_tag
def get_momentjs_language_static(language: str) -> str:
    """
    Get the correct language code URL for Moment.JS

    :param language: Django's language code
    :type language: str
    :return: Mapped language code
    :rtype: str
    """

    mapped_language = get_momentjs_language_code(language)

    static_url = (
        static(path=f"allianceauth/libs/moment.js/2.29.4/locale/{mapped_language}.js")
        if mapped_language
        else ""
    )

    return static_url

@register.simple_tag
def get_relative_momentjs_language_path(language: str) -> str:
    """
    Get the correct language code URL for Moment.JS (relative path to the static folder)

    :param language: Django's language code
    :type language: str
    :return: Mapped language code path
    :rtype: str
    """

    mapped_language = get_momentjs_language_code(language)

    static_url = (
        f"allianceauth/libs/moment.js/2.29.4/locale/{mapped_language}.js"
        if mapped_language
        else ""
    )

    return static_url
