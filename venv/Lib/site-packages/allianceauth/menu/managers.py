from __future__ import annotations  # Still needed for Python 3.8, replaced with better implementations in Py39+

import logging
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Case, Q, Value, When

from allianceauth.hooks import get_hooks

from .constants import MenuItemType
from .core.menu_item_hooks import MenuItemHookParams, gather_params

if TYPE_CHECKING:
    from .models import MenuItem


logger = logging.getLogger(__name__)


class MenuItemQuerySet(models.QuerySet):
    def filter_folders(self):
        """Add filter to include folders only."""
        return self.filter(hook_hash__isnull=True, url="")

    def annotate_item_type_2(self):
        """Add calculated field with item type."""
        return self.annotate(
            item_type_2=Case(
                When(~Q(hook_hash__isnull=True), then=Value(MenuItemType.APP.value)),
                When(url="", then=Value(MenuItemType.FOLDER.value)),
                default=Value(MenuItemType.LINK.value),
            )
        )


class MenuItemManagerBase(models.Manager):
    def sync_all(self):
        """Sync all menu items from hooks."""
        hook_params = self._gather_menu_item_hook_params()
        self._delete_obsolete_app_items(hook_params)
        self._update_or_create_app_items(hook_params)

    def _gather_menu_item_hook_params(self) -> list[MenuItemHookParams]:
        params = [gather_params(hook()) for hook in get_hooks("menu_item_hook")]
        return params

    def _delete_obsolete_app_items(self, params: list[MenuItemHookParams]):
        hashes = [obj.hash for obj in params]
        self.exclude(hook_hash__isnull=True).exclude(hook_hash__in=hashes).delete()

    def _update_or_create_app_items(self, params: list[MenuItemHookParams]):
        for param in params:
            try:
                obj: MenuItem = self.get(hook_hash=param.hash)
            except self.model.DoesNotExist:
                self.create(hook_hash=param.hash, order=param.order, text=param.text)
            else:
                # if it exists update the text only
                if obj.text != param.text:
                    obj.text = param.text
                    obj.save()

        logger.debug("Updated menu items from %d menu item hooks", len(params))


MenuItemManager = MenuItemManagerBase.from_queryset(MenuItemQuerySet)
