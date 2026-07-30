from allianceauth.menu.hooks import MenuItemHook
from . import urls
from django.utils.translation import gettext_lazy as _
from allianceauth import hooks
from allianceauth.services.hooks import UrlHook


@hooks.register('menu_item_hook')
def register_menu():
    return MenuItemHook(_('Fleet Activity Tracking'), 'fa-solid fa-users', 'fatlink:view',
                        navactive=['fatlink:'])


@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'fatlink', r'^fat/')
