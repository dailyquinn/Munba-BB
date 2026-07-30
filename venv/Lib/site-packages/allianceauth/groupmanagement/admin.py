from django.apps import apps
from django.contrib import admin

from django.contrib.auth.models import Group as BaseGroup, Permission, User
from django.db.models import Count, Exists, OuterRef
from django.db.models.functions import Lower
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save
)
from django.dispatch import receiver

from .forms import GroupAdminForm, ReservedGroupNameAdminForm
from .models import AuthGroup, GroupRequest, ReservedGroupName
from .tasks import remove_users_not_matching_states_from_group

if 'eve_autogroups' in apps.app_configs:
    _has_auto_groups = True
else:
    _has_auto_groups = False


class AuthGroupInlineAdmin(admin.StackedInline):
    model = AuthGroup
    filter_horizontal = ('group_leaders', 'group_leader_groups', 'states',)
    fields = (
        'description',
        'group_leaders',
        'group_leader_groups',
        'states',
        'internal',
        'hidden',
        'open',
        'public',
        'restricted',
    )
    verbose_name_plural = 'Auth Settings'
    verbose_name = ''

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """overriding this formfield to have sorted lists in the form"""
        if db_field.name == "group_leaders":
            kwargs["queryset"] = User.objects.order_by(Lower('username'))
        elif db_field.name == "group_leader_groups":
            kwargs["queryset"] = Group.objects.order_by(Lower('name'))
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('auth.change_group')

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ("restricted",)
        return self.readonly_fields


if _has_auto_groups:
    class IsAutoGroupFilter(admin.SimpleListFilter):
        title = 'auto group'
        parameter_name = 'is_auto_group__exact'

        def lookups(self, request, model_admin):
            return (
                ('yes', 'Yes'),
                ('no', 'No'),
            )

        def queryset(self, request, queryset):
            value = self.value()
            if value == 'yes':
                return queryset.exclude(
                    managedalliancegroup__isnull=True,
                    managedcorpgroup__isnull=True
                )
            elif value == 'no':
                return queryset.filter(
                    managedalliancegroup__isnull=True,
                    managedcorpgroup__isnull=True
                )
            return queryset


class HasLeaderFilter(admin.SimpleListFilter):
    title = 'has leader'
    parameter_name = 'has_leader__exact'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.filter(authgroup__group_leaders__isnull=False)
        elif value == 'no':
            return queryset.filter(authgroup__group_leaders__isnull=True)
        return queryset


class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    ordering = ('name',)
    list_display = (
        'name',
        '_description',
        '_properties',
        '_member_count',
        'has_leader',
    )
    list_filter = [
        'authgroup__internal',
        'authgroup__hidden',
        'authgroup__open',
        'authgroup__public',
    ]
    if _has_auto_groups:
        list_filter.append(IsAutoGroupFilter)
    list_filter.append(HasLeaderFilter)

    search_fields = ('name', 'authgroup__description')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        has_leader_qs = (
            AuthGroup.objects.filter(group=OuterRef('pk'), group_leaders__isnull=False)
        )
        has_leader_groups_qs = (
            AuthGroup.objects.filter(
                group=OuterRef('pk'), group_leader_groups__isnull=False
            )
        )
        qs = (
            qs.select_related('authgroup')
            .annotate(member_count=Count('user', distinct=True))
            .annotate(has_leader=Exists(has_leader_qs))
            .annotate(has_leader_groups=Exists(has_leader_groups_qs))
        )
        if _has_auto_groups:
            is_autogroup_corp = (
                Group.objects.filter(
                    pk=OuterRef('pk'), managedcorpgroup__isnull=False
                )
            )
            is_autogroup_alliance = (
                Group.objects.filter(
                    pk=OuterRef('pk'), managedalliancegroup__isnull=False
                )
            )
            qs = (
                qs.annotate(is_autogroup_corp=Exists(is_autogroup_corp))
                .annotate(is_autogroup_alliance=Exists(is_autogroup_alliance))
            )
        return qs

    def _description(self, obj):
        return obj.authgroup.description

    @admin.display(description='Members', ordering='member_count')
    def _member_count(self, obj):
        return obj.member_count

    @admin.display(boolean=True)
    def has_leader(self, obj):
        return obj.has_leader or obj.has_leader_groups

    def _properties(self, obj):
        properties = list()
        if _has_auto_groups and (obj.is_autogroup_corp or obj.is_autogroup_alliance):
            properties.append('Auto Group')
        elif obj.authgroup.internal:
            properties.append('Internal')
        else:
            if obj.authgroup.hidden:
                properties.append('Hidden')
            if obj.authgroup.open:
                properties.append('Open')
            if obj.authgroup.public:
                properties.append('Public')
        if not properties:
            properties.append('Default')
        if obj.authgroup.restricted:
            properties.append('Restricted')
        return properties

    filter_horizontal = ('permissions',)
    inlines = (AuthGroupInlineAdmin,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            kwargs["queryset"] = Permission.objects.select_related("content_type").all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_formset(self, request, form, formset, change):
        for inline_form in formset:
            ag_instance = inline_form.save(commit=False)
            ag_instance.group = form.instance
            ag_instance.save()
            if ag_instance.states.exists():
                remove_users_not_matching_states_from_group.delay(ag_instance.group.pk)
        formset.save()

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ("permissions",)
        return self.readonly_fields


class Group(BaseGroup):
    class Meta:
        proxy = True
        verbose_name = BaseGroup._meta.verbose_name
        verbose_name_plural = BaseGroup._meta.verbose_name_plural


try:
    admin.site.unregister(BaseGroup)
finally:
    admin.site.register(Group, GroupAdmin)


@admin.register(GroupRequest)
class GroupRequestAdmin(admin.ModelAdmin):
    search_fields = ('user__username', )
    list_display = ('id', 'group', 'user', '_leave_request')
    list_filter = (
        ('group', admin.RelatedOnlyFieldListFilter),
        ('user', admin.RelatedOnlyFieldListFilter),
        'leave_request',
    )

    @admin.display(boolean=True, description="is leave request")
    def _leave_request(self, obj) -> True:
        return obj.leave_request


@admin.register(ReservedGroupName)
class ReservedGroupNameAdmin(admin.ModelAdmin):
    form = ReservedGroupNameAdminForm
    list_display = ("name", "created_by", "created_at")

    def get_form(self, request, *args, **kwargs):
        form = super().get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False


@receiver(pre_save, sender=Group)
def redirect_pre_save(sender, signal=None, *args, **kwargs):
    pre_save.send(BaseGroup, *args, **kwargs)


@receiver(post_save, sender=Group)
def redirect_post_save(sender, signal=None, *args, **kwargs):
    post_save.send(BaseGroup, *args, **kwargs)


@receiver(pre_delete, sender=Group)
def redirect_pre_delete(sender, signal=None, *args, **kwargs):
    pre_delete.send(BaseGroup, *args, **kwargs)


@receiver(post_delete, sender=Group)
def redirect_post_delete(sender, signal=None, *args, **kwargs):
    post_delete.send(BaseGroup, *args, **kwargs)


@receiver(m2m_changed, sender=Group.permissions.through)
def redirect_m2m_changed_permissions(sender, signal=None, *args, **kwargs):
    m2m_changed.send(BaseGroup, *args, **kwargs)
