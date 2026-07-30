"""Template tags for rendering the classic side menu."""

from django import template
from django.http import HttpRequest

from allianceauth.hooks import get_hooks

register = template.Library()


# TODO: Show user created menu items
# TODO: Apply is_hidden feature for BS3 type items


@register.inclusion_tag("public/menublock.html", takes_context=True)
def menu_items(context: dict) -> dict:
    """Render menu items for classic dashboard."""
    items = render_menu(context["request"])
    return {"menu_items": items}


def render_menu(request: HttpRequest):
    """Return the rendered side menu for including in a template.

    This function is creating a BS3 style menu.
    """

    hooks = get_hooks("menu_item_hook")
    raw_items = [fn() for fn in hooks]
    raw_items.sort(key=lambda i: i.order)
    menu_items = [item.render(request) for item in raw_items]
    return menu_items
