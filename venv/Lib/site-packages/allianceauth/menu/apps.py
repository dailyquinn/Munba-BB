import logging

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# TODO discuss permissions for user defined links
# TODO define aa way for hooks to predefine a "parent" to create a sub menu from modules
# TODO Add user documentation


class MenuConfig(AppConfig):
    name = "allianceauth.menu"
    label = "menu"
    verbose_name = _("Menu")

    def ready(self):
        from allianceauth.menu.core import smart_sync

        smart_sync.reset_menu_items_sync()
