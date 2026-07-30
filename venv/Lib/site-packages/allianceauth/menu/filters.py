"""Filters for the menu app."""

from django.contrib import admin
from django.utils.translation import gettext_noop as _

from allianceauth.menu.constants import MenuItemType


class MenuItemTypeListFilter(admin.SimpleListFilter):
    """Allow filtering admin changelist by menu item type."""

    title = _("type")
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [(obj.value, obj.label.title()) for obj in MenuItemType]

    def queryset(self, request, queryset):
        if value := self.value():
            return queryset.annotate_item_type_2().filter(
                item_type_2=MenuItemType(value).value
            )

        return None
