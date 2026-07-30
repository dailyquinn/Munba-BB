from allianceauth.menu.hooks import MenuItemHook
from allianceauth.optimer.views import dashboard_ops
from allianceauth.services.hooks import UrlHook
from django.utils.translation import gettext_lazy as _
from allianceauth import hooks
from . import urls


class OpTimerboardMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self, _('Fleet Operations'),
            'fa-solid fa-exclamation',
            'optimer:view',
            navactive=['optimer:']
        )

    def render(self, request):
        if request.user.has_perm('auth.optimer_view'):
            return MenuItemHook.render(self, request)
        return ''


@hooks.register('menu_item_hook')
def register_menu():
    return OpTimerboardMenu()


@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'optimer', r'^optimer/')


class NextOpsHook(hooks.DashboardItemHook):
    def __init__(self): #TODO add the view perms so if they cant see it is not rendered
        hooks.DashboardItemHook.__init__(
            self,
            dashboard_ops,
            6
        )


@hooks.register('dashboard_hook')
def register_groups_hook():
    return NextOpsHook()
