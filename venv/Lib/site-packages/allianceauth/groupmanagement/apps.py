from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GroupManagementConfig(AppConfig):
    name = 'allianceauth.groupmanagement'
    label = 'groupmanagement'
    verbose_name = _('Group Management')

    def ready(self):
        from . import signals  # noqa: F401
