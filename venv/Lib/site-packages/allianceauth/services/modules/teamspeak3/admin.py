from django.contrib import admin
from django.contrib.auth.models import Group
from .models import AuthTS, Teamspeak3User, StateGroup, TSgroup
from ...admin import ServicesUserAdmin
from allianceauth.groupmanagement.models import ReservedGroupName


@admin.register(Teamspeak3User)
class Teamspeak3UserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + (
        'uid',
        'perm_key'
    )
    search_fields = ServicesUserAdmin.search_fields + ('uid', )


@admin.register(AuthTS)
class AuthTSgroupAdmin(admin.ModelAdmin):
    change_list_template = 'admin/teamspeak3/authts/change_list.html'
    ordering = ('auth_group__name', )
    list_select_related = True

    list_display = ('auth_group', '_ts_group')
    list_filter = ('ts_group', )

    fields = ('auth_group', 'ts_group')
    filter_horizontal = ('ts_group',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'auth_group':
            kwargs['queryset'] = Group.objects.exclude(name__in=ReservedGroupName.objects.values_list('name', flat=True))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'ts_group':
            kwargs['queryset'] = TSgroup.objects.exclude(ts_group_name__in=ReservedGroupName.objects.values_list('name', flat=True))
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(
        description='ts groups'
    )
    def _ts_group(self, obj):
        return [x for x in obj.ts_group.all().order_by('ts_group_id')]

    # _ts_group.admin_order_field = 'profile__state'


@admin.register(StateGroup)
class StateGroupAdmin(admin.ModelAdmin):
    list_display = ('state', 'ts_group')
    search_fields = ('state__name', 'ts_group__ts_group_name')
