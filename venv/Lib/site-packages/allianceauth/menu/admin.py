"""Admin site for menu app."""

from typing import Optional

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_noop as _

from .constants import MenuItemType
from .core.smart_sync import sync_menu
from .filters import MenuItemTypeListFilter
from .forms import (
    AppMenuItemAdminForm,
    FolderMenuItemAdminForm,
    LinkMenuItemAdminForm,
)
from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "_text",
        "parent",
        "order",
        "_user_defined",
        "_visible",
        "_children",
    )
    list_filter = [
        MenuItemTypeListFilter,
        "is_hidden",
        ("parent", admin.RelatedOnlyFieldListFilter),
    ]
    ordering = ["parent", "order", "text"]

    def get_form(self, request: HttpRequest, obj: Optional[MenuItem] = None, **kwargs):
        kwargs["form"] = self._choose_form(request, obj)
        return super().get_form(request, obj, **kwargs)

    @classmethod
    def _choose_form(cls, request: HttpRequest, obj: Optional[MenuItem]):
        """Return the form for the current menu item type."""
        if obj:  # change
            if obj.hook_hash:
                return AppMenuItemAdminForm

            if obj.is_folder:
                return FolderMenuItemAdminForm

            return LinkMenuItemAdminForm

        # add
        if cls._type_from_request(request) is MenuItemType.FOLDER:
            return FolderMenuItemAdminForm

        return LinkMenuItemAdminForm

    def add_view(self, request, form_url="", extra_context=None) -> HttpResponse:
        context = extra_context or {}
        item_type = self._type_from_request(request, default=MenuItemType.LINK)
        context["title"] = _("Add %s menu item") % item_type.label
        return super().add_view(request, form_url, context)

    def change_view(
        self, request, object_id, form_url="", extra_context=None
    ) -> HttpResponse:
        extra_context = extra_context or {}
        obj = get_object_or_404(MenuItem, id=object_id)
        extra_context["title"] = _("Change %s menu item") % obj.item_type.label
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request: HttpRequest, extra_context=None):
        # needed to ensure items are updated after an app change
        # and when the admin page is opened directly
        sync_menu()
        extra_context = extra_context or {}
        extra_context["folder_type"] = MenuItemType.FOLDER.value
        return super().changelist_view(request, extra_context)

    @admin.display(description=_("children"))
    def _children(self, obj: MenuItem):
        if not obj.is_folder:
            return []

        names = [obj.text for obj in obj.children.order_by("order", "text")]
        return names if names else "?"

    @admin.display(description=_("text"), ordering="text")
    def _text(self, obj: MenuItem) -> str:
        if obj.is_folder:
            return f"[{obj.text}]"
        return obj.text

    @admin.display(description=_("user defined"), boolean=True)
    def _user_defined(self, obj: MenuItem) -> bool:
        return obj.is_user_defined

    @admin.display(description=_("visible"), ordering="is_hidden", boolean=True)
    def _visible(self, obj: MenuItem) -> bool:
        return not bool(obj.is_hidden)

    @staticmethod
    def _type_from_request(
        request: HttpRequest, default=None
    ) -> Optional[MenuItemType]:
        try:
            return MenuItemType(request.GET.get("type"))
        except ValueError:
            return default
