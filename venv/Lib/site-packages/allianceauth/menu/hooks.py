"""Menu item hooks."""

from typing import List, Optional

from django.template.loader import render_to_string

from allianceauth.menu.constants import DEFAULT_MENU_ITEM_ORDER


class MenuItemHook:
    """Auth Hook for generating side menu items.

    Args:
        - text: The text shown as menu item, e.g. usually the name of the app.
        - classes: The classes that should be applied to the menu item icon
        - url_name: The name of the Django URL to use
        - order: An integer which specifies the order of the menu item,
            lowest to highest. Community apps are free to use any order above `1000`.
            Numbers below are served for Auth.
        - A list of views or namespaces the link should be highlighted on.
            See 3rd party package django-navhelper for usage.
                Defaults to the supplied `url_name`.


    Optional:
        - count is an integer shown next to the menu item as badge when is is not `None`.
            Apps need to set the count in their child class, e.g. in `render()` method

    """

    def __init__(
        self,
        text: str,
        classes: str,
        url_name: str,
        order: Optional[int] = None,
        navactive: Optional[List[str]] = None,
    ):
        self.text = text
        self.classes = classes
        self.url_name = url_name
        self.template = "public/menuitem.html"
        self.order = order if order is not None else DEFAULT_MENU_ITEM_ORDER
        self.count = None

        navactive = navactive or []
        navactive.append(url_name)
        self.navactive = navactive

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(text="{self.text}")'

    def render(self, request) -> str:
        """Render this menu item and return resulting HTML."""
        return render_to_string(self.template, {"item": self}, request=request)
