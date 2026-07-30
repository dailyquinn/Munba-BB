"""
Custom template tags for custom_css app
"""

# Alliance Auth Custom CSS
from allianceauth.custom_css.models import CustomCSS

# Django
from django.template.defaulttags import register
from django.utils.safestring import mark_safe


@register.simple_tag
def return_custom_css() -> str:
    """
    Template tag to load custom CSS

    :return:
    :rtype:
    """

    css = CustomCSS.get_solo()

    return (
        mark_safe(f"<style>{css.css_compressed}</style>") if css.css_compressed else ""
    )
