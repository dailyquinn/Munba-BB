from django.contrib import admin
from django.db import models
from .models import AutogroupsConfig, ManagedCorpGroup, ManagedAllianceGroup

import logging


logger = logging.getLogger(__name__)


def sync_user_groups(modeladmin, request, queryset):
    for agc in queryset:
        logger.debug(f"update_all_states_group_membership for {agc}")
        agc.update_all_states_group_membership()


@admin.register(AutogroupsConfig)
class AutogroupsConfigAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'strip': False}
    }

    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is the case when obj is already created i.e. it's an edit
            return [
                'corp_group_prefix', 'corp_name_source', 'alliance_group_prefix', 'alliance_name_source',
                'replace_spaces', 'replace_spaces_with'
            ]
        else:
            return []

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['sync_user_groups'] = (sync_user_groups,
                                        'sync_user_groups',
                                        'Sync all users groups for this Autogroup Config')
        return actions


admin.site.register(ManagedCorpGroup)
admin.site.register(ManagedAllianceGroup)
