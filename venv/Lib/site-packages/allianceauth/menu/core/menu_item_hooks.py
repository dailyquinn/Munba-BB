"""Logic for handling MenuItemHook objects."""

import hashlib
from typing import List, NamedTuple, Optional

from allianceauth.menu.hooks import MenuItemHook


class MenuItemHookCustom(MenuItemHook):
    """A user defined menu item that can be rendered with the standard template."""

    def __init__(
        self,
        text: str,
        classes: str,
        url_name: str,
        order: Optional[int] = None,
        navactive: Optional[List[str]] = None,
    ):
        super().__init__(text, classes, url_name, order, navactive)
        self.url = ""
        self.is_folder = None
        self.html_id = ""
        self.children = []


class MenuItemHookParams(NamedTuple):
    """Immutable container for params about a menu item hook."""

    text: str
    order: int
    hash: str


def generate_hash(obj: MenuItemHook) -> str:
    """Return the hash for a menu item hook."""
    my_class = obj.__class__
    name = f"{my_class.__module__}.{my_class.__name__}"
    hash_value = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return hash_value


def gather_params(obj: MenuItemHook) -> MenuItemHookParams:
    """Return params from a menu item hook."""
    text = getattr(obj, "text", obj.__class__.__name__)
    order = getattr(obj, "order", None)
    hash = generate_hash(obj)
    return MenuItemHookParams(text=text, hash=hash, order=order)
