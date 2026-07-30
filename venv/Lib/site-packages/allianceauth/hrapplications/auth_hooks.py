from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.menu.hooks import MenuItemHook
from allianceauth.services.hooks import UrlHook

from . import urls
from .models import Application


class ApplicationsMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            _('Applications'),
            'fa-regular fa-file',
            'hrapplications:index',
            navactive=['hrapplications:'])

    def render(self, request):
        app_count = Application.objects.pending_requests_count_for_user(request.user)
        self.count = app_count if app_count and app_count > 0 else None
        return MenuItemHook.render(self, request)


@hooks.register('menu_item_hook')
def register_menu():
    return ApplicationsMenu()


class ApplicationsUrls(UrlHook):
    def __init__(self):
        UrlHook.__init__(self, urls, 'hrapplications', r'^hr/')


@hooks.register('url_hook')
def register_url():
    return ApplicationsUrls()
