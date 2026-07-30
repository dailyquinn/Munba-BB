"""Provide capability to sync menu items when needed only."""

from django.core.cache import cache

_MENU_SYNC_CACHE_KEY = "ALLIANCEAUTH-MENU-SYNCED"


def sync_menu() -> None:
    """Sync menu items if needed only."""
    from allianceauth.menu.models import MenuItem

    is_sync_needed = not _is_menu_synced() or not MenuItem.objects.exists()
    # need to also check for existence of MenuItems in database
    # to ensure the menu is synced during tests
    if is_sync_needed:
        MenuItem.objects.sync_all()
        _record_menu_was_synced()


def _is_menu_synced() -> bool:
    return cache.get(_MENU_SYNC_CACHE_KEY, False)


def _record_menu_was_synced() -> None:
    cache.set(_MENU_SYNC_CACHE_KEY, True, timeout=None)  # no timeout


def reset_menu_items_sync() -> None:
    """Ensure menu items are synced, e.g. after a Django restart."""
    cache.delete(_MENU_SYNC_CACHE_KEY)
