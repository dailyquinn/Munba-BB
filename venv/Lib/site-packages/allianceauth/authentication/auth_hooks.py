from allianceauth.hooks import DashboardItemHook
from allianceauth import hooks
from .views import dashboard_characters, dashboard_esi_check, dashboard_groups, dashboard_admin


class UserCharactersHook(DashboardItemHook):
    def __init__(self):
        DashboardItemHook.__init__(
            self,
            dashboard_characters,
            5
        )


class UserGroupsHook(DashboardItemHook):
    def __init__(self):
        DashboardItemHook.__init__(
            self,
            dashboard_groups,
            5
        )


class AdminHook(DashboardItemHook):
    def __init__(self):
        DashboardItemHook.__init__(
            self,
            dashboard_admin,
            1
        )


class ESICheckHook(DashboardItemHook):
    def __init__(self):
        DashboardItemHook.__init__(
            self,
            dashboard_esi_check,
            0
        )


@hooks.register('dashboard_hook')
def register_character_hook():
    return UserCharactersHook()


@hooks.register('dashboard_hook')
def register_groups_hook():
    return UserGroupsHook()


@hooks.register('dashboard_hook')
def register_admin_hook():
    return AdminHook()


@hooks.register('dashboard_hook')
def register_esi_hook():
    return ESICheckHook()
