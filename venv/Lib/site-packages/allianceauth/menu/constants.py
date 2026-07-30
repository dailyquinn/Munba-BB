"""Global constants for the menu app."""

from django.db import models
from django.utils.translation import gettext_lazy as _

DEFAULT_FOLDER_ICON_CLASSES = "fa-solid fa-folder"  # TODO: Make this a setting?
"""Default icon class for folders."""

DEFAULT_MENU_ITEM_ORDER = 9999
"""Default order for any menu item."""


class MenuItemType(models.TextChoices):
    """The type of a menu item."""

    APP = "app", _("app")
    FOLDER = "folder", _("folder")
    LINK = "link", _("link")
