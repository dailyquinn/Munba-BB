from allianceauth.menu.hooks import MenuItemHook
from allianceauth.services.hooks import UrlHook
from django.utils.translation import gettext_lazy as _
from allianceauth import hooks
from allianceauth.corputils import urls


class CorpStats(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            _('Corporation Stats'),
            'fa-solid fa-share-nodes',
            'corputils:view',
            navactive=['corputils:']
        )

    def render(self, request):
        if request.user.has_perm('corputils.view_corp_corpstats') or request.user.has_perm(
                'corputils.view_alliance_corpstats') or request.user.has_perm(
                'corputils.add_corpstats') or request.user.has_perm('corputils.view_state_corpstats'):
            return MenuItemHook.render(self, request)
        return ''


@hooks.register('menu_item_hook')
def register_menu():
    return CorpStats()


@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'corputils', r'^corpstats/')
