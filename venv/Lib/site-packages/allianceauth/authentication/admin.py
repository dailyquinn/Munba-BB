from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission as BasePermission
from django.contrib.auth.models import User as BaseUser
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save
)
from django.dispatch import receiver
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify

from allianceauth.authentication.models import (
    CharacterOwnership,
    OwnershipRecord,
    State,
    UserProfile,
    get_guest_state
)
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
    EveFactionInfo
)
from allianceauth.eveonline.tasks import update_character
from allianceauth.hooks import get_hooks
from allianceauth.services.hooks import ServicesHook

from .app_settings import (
    AUTHENTICATION_ADMIN_USERS_MAX_CHARS,
    AUTHENTICATION_ADMIN_USERS_MAX_GROUPS
)
from .forms import UserChangeForm, UserProfileForm


def make_service_hooks_update_groups_action(service):
    """
    Make a admin action for the given service
    :param service: services.hooks.ServicesHook
    :return: fn to update services groups for the selected users
    """
    def update_service_groups(modeladmin, request, queryset):
        if hasattr(service, 'update_groups_bulk'):
            service.update_groups_bulk(queryset)
        else:
            for user in queryset:  # queryset filtering doesn't work here?
                service.update_groups(user)

    update_service_groups.__name__ = str(f'update_{slugify(service.name)}_groups')
    update_service_groups.short_description = f"Sync groups for selected {service.title} accounts"
    return update_service_groups


def make_service_hooks_sync_nickname_action(service):
    """
    Make a sync_nickname admin action for the given service
    :param service: services.hooks.ServicesHook
    :return: fn to sync nickname for the selected users
    """
    def sync_nickname(modeladmin, request, queryset):
        if hasattr(service, 'sync_nicknames_bulk'):
            service.sync_nicknames_bulk(queryset)
        else:
            for user in queryset:  # queryset filtering doesn't work here?
                service.sync_nickname(user)

    sync_nickname.__name__ = str(f'sync_{slugify(service.name)}_nickname')
    sync_nickname.short_description = f"Sync nicknames for selected {service.title} accounts"
    return sync_nickname


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    readonly_fields = ('state',)
    form = UserProfileForm
    verbose_name = ''
    verbose_name_plural = 'Profile'

    def get_formset(self, request, obj=None, **kwargs):
        # main_character field can only show current value or unclaimed alts
        # if superuser, allow selecting from any unclaimed main
        query = Q()
        if obj and obj.profile.main_character:
            query |= Q(pk=obj.profile.main_character_id)
            if request.user.is_superuser:
                query |= Q(userprofile__isnull=True)
            else:
                query |= Q(character_ownership__user=obj)
        formset = super().get_formset(request, obj=obj, **kwargs)

        def get_kwargs(self, index):
            return {'querysets': {'main_character': EveCharacter.objects.filter(query)}}
        formset.get_form_kwargs = get_kwargs
        return formset

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.display(description="")
def user_profile_pic(obj):
    """profile pic column data for user objects

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists (requires CSS)
    """
    user_obj = obj.user if hasattr(obj, 'user') else obj
    if user_obj.profile.main_character:
        return format_html(
            '<img src="{}" class="img-circle">',
            user_obj.profile.main_character.portrait_url(size=32)
        )
    return None


@admin.display(description="user / main", ordering="username")
def user_username(obj):
    """user column data for user objects

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists
    """
    link = reverse(
        'admin:{}_{}_change'.format(
            obj._meta.app_label,
            type(obj).__name__.lower()
        ),
        args=(obj.pk,)
    )
    user_obj = obj.user if hasattr(obj, 'user') else obj
    if user_obj.profile.main_character:
        return format_html(
            '<strong><a href="{}">{}</a></strong><br>{}',
            link,
            user_obj.username,
            user_obj.profile.main_character.character_name
        )
    return format_html(
        '<strong><a href="{}">{}</a></strong>',
        link,
        user_obj.username,
    )


@admin.display(
    description="Corporation / Alliance (Main)",
    ordering="profile__main_character__corporation_name"
)
def user_main_organization(obj):
    """main organization column data for user objects

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists
    """
    user_obj = obj.user if hasattr(obj, 'user') else obj
    if not user_obj.profile.main_character:
        return ''
    result = user_obj.profile.main_character.corporation_name
    if user_obj.profile.main_character.alliance_id:
        result += f'<br>{user_obj.profile.main_character.alliance_name}'
    elif user_obj.profile.main_character.faction_name:
        result += f'<br>{user_obj.profile.main_character.faction_name}'
    return format_html(result)


class MainCorporationsFilter(admin.SimpleListFilter):
    """Custom filter to filter on corporations from mains only

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists
    """
    title = 'corporation'
    parameter_name = 'main_corporation_id__exact'

    def lookups(self, request, model_admin):
        qs = EveCharacter.objects\
            .exclude(userprofile=None)\
            .values('corporation_id', 'corporation_name')\
            .distinct()\
            .order_by(Lower('corporation_name'))
        return tuple(
            (x['corporation_id'], x['corporation_name']) for x in qs
        )

    def queryset(self, request, qs):
        if self.value() is None:
            return qs.all()
        if qs.model == User:
            return qs.filter(
                profile__main_character__corporation_id=self.value()
            )
        return qs.filter(
            user__profile__main_character__corporation_id=self.value()
        )


class MainAllianceFilter(admin.SimpleListFilter):
    """Custom filter to filter on alliances from mains only

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists
    """
    title = 'alliance'
    parameter_name = 'main_alliance_id__exact'

    def lookups(self, request, model_admin):
        qs = (
            EveCharacter.objects
            .exclude(alliance_id=None)
            .exclude(userprofile=None)
            .values('alliance_id', 'alliance_name')
            .distinct()
            .order_by(Lower('alliance_name'))
        )
        return tuple(
            (x['alliance_id'], x['alliance_name']) for x in qs
        )

    def queryset(self, request, qs):
        if self.value() is None:
            return qs.all()
        if qs.model == User:
            return qs.filter(profile__main_character__alliance_id=self.value())
        return qs.filter(
            user__profile__main_character__alliance_id=self.value()
        )


class MainFactionFilter(admin.SimpleListFilter):
    """Custom filter to filter on factions from mains only

    works for both User objects and objects with `user` as FK to User
    To be used for all user based admin lists
    """
    title = 'faction'
    parameter_name = 'main_faction_id__exact'

    def lookups(self, request, model_admin):
        qs = (
            EveCharacter.objects
            .exclude(faction_id=None)
            .exclude(userprofile=None)
            .values('faction_id', 'faction_name')
            .distinct()
            .order_by(Lower('faction_name'))
        )
        return tuple(
            (x['faction_id'], x['faction_name']) for x in qs
        )

    def queryset(self, request, qs):
        if self.value() is None:
            return qs.all()
        if qs.model == User:
            return qs.filter(profile__main_character__faction_id=self.value())
        return qs.filter(
            user__profile__main_character__faction_id=self.value()
        )


@admin.display(description="Update main character model from ESI")
def update_main_character_model(modeladmin, request, queryset):
    tasks_count = 0
    for obj in queryset:
        if obj.profile.main_character:
            update_character.delay(obj.profile.main_character.character_id)
            tasks_count += 1

    modeladmin.message_user(
        request, f'Update from ESI started for {tasks_count} characters'
    )


class UserAdmin(BaseUserAdmin):
    """Extending Django's UserAdmin model

    Behavior of groups and characters columns can be configured via settings
    """

    inlines = [UserProfileInline]
    ordering = ('username', )
    list_select_related = ('profile__state', 'profile__main_character')
    show_full_result_count = True
    list_display = (
        user_profile_pic,
        user_username,
        '_state',
        '_groups',
        user_main_organization,
        '_characters',
        'is_active',
        'date_joined',
        '_role'
    )
    list_display_links = None
    list_filter = (
        'profile__state',
        'groups',
        MainCorporationsFilter,
        MainAllianceFilter,
        MainFactionFilter,
        'is_active',
        'date_joined',
        'is_staff',
        'is_superuser'
    )
    search_fields = ('username', 'character_ownerships__character__character_name')
    readonly_fields = ('date_joined', 'last_login')
    filter_horizontal = ('groups', 'user_permissions',)
    form = UserChangeForm

    class Media:
        css = {
            "all": ("allianceauth/authentication/css/admin.css",)
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("character_ownerships__character", "groups")

    def get_form(self, request, obj=None, **kwargs):
        """Inject current request into change form object."""

        MyForm = super().get_form(request, obj, **kwargs)
        if obj:
            class MyFormInjected(MyForm):
                def __new__(cls, *args, **kwargs):
                    kwargs['request'] = request
                    return MyForm(*args, **kwargs)

            return MyFormInjected
        return MyForm

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions[update_main_character_model.__name__] = (
            update_main_character_model,
            update_main_character_model.__name__,
            update_main_character_model.short_description
        )

        for hook in get_hooks('services_hook'):
            svc = hook()
            # Check update_groups is redefined/overloaded
            if svc.update_groups.__module__ != ServicesHook.update_groups.__module__:
                action = make_service_hooks_update_groups_action(svc)
                actions[action.__name__] = (
                    action,
                    action.__name__,
                    action.short_description
                )

            # Create sync nickname action if service implements it
            if svc.sync_nickname.__module__ != ServicesHook.sync_nickname.__module__:
                action = make_service_hooks_sync_nickname_action(svc)
                actions[action.__name__] = (
                    action, action.__name__,
                    action.short_description
                )
        return actions

    def _list_2_html_w_tooltips(self, my_items: list, max_items: int) -> str:
        """converts list of strings into HTML with cutoff and tooltip"""
        items_truncated_str = ', '.join(my_items[:max_items])
        if not my_items:
            result = None
        elif len(my_items) <= max_items:
            result = items_truncated_str
        else:
            items_truncated_str += ', (...)'
            items_all_str = ', '.join(my_items)
            result = format_html(
                '<span data-tooltip="{}" class="tooltip">{}</span>',
                items_all_str,
                items_truncated_str
            )
        return result

    def _characters(self, obj):
        character_ownerships = list(obj.character_ownerships.all())
        characters = [obj.character.character_name for obj in character_ownerships]
        return self._list_2_html_w_tooltips(
            sorted(characters),
            AUTHENTICATION_ADMIN_USERS_MAX_CHARS
        )

    @admin.display(ordering="profile__state")
    def _state(self, obj):
        return obj.profile.state.name

    def _groups(self, obj):
        my_groups = sorted(group.name for group in list(obj.groups.all()))
        return self._list_2_html_w_tooltips(
            my_groups, AUTHENTICATION_ADMIN_USERS_MAX_GROUPS
        )

    def _role(self, obj):
        if obj.is_superuser:
            role = 'Superuser'
        elif obj.is_staff:
            role = 'Staff'
        else:
            role = 'User'
        return role

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('auth.change_user')

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm('auth.add_user')

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('auth.delete_user')

    def get_object(self, *args , **kwargs):
        obj = super().get_object(*args , **kwargs)
        self.obj = obj  # storing current object for use in formfield_for_manytomany
        return obj

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups":
            groups_qs = Group.objects.filter(authgroup__states__isnull=True)
            obj_state = self.obj.profile.state
            if obj_state:
                matching_groups_qs = Group.objects.filter(authgroup__states=obj_state)
                groups_qs = groups_qs | matching_groups_qs
            kwargs["queryset"] = groups_qs.order_by(Lower("name"))
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return self.readonly_fields + (
                "is_staff", "is_superuser", "user_permissions"
            )
        return self.readonly_fields


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ('name', 'priority', '_user_count')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(user_count=Count("userprofile__id"))

    @admin.display(description="Users", ordering="user_count")
    def _user_count(self, obj):
        return obj.user_count

    fieldsets = (
        (None, {
            'fields': ('name', 'permissions', 'priority'),
        }),
        ('Membership', {
            'fields': (
                'public',
                'member_characters',
                'member_corporations',
                'member_alliances',
                'member_factions'
            ),
        })
    )
    filter_horizontal = [
        'member_characters',
        'member_corporations',
        'member_alliances',
        'member_factions',
        'permissions'
    ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """overriding this formfield to have sorted lists in the form"""
        if db_field.name == "member_characters":
            kwargs["queryset"] = EveCharacter.objects.all()\
                .order_by(Lower('character_name'))
        elif db_field.name == "member_corporations":
            kwargs["queryset"] = EveCorporationInfo.objects.all()\
                .order_by(Lower('corporation_name'))
        elif db_field.name == "member_alliances":
            kwargs["queryset"] = EveAllianceInfo.objects.all()\
                .order_by(Lower('alliance_name'))
        elif db_field.name == "member_factions":
            kwargs["queryset"] = EveFactionInfo.objects.all()\
                .order_by(Lower('faction_name'))
        elif db_field.name == "permissions":
            kwargs["queryset"] = Permission.objects.select_related("content_type").all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        if obj == get_guest_state():
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_fieldsets(self, request, obj=None):
        if obj == get_guest_state():
            return (
                (None, {
                    'fields': ('permissions', 'priority'),
                }),
            )
        return super().get_fieldsets(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ("permissions",)
        return self.readonly_fields


class BaseOwnershipAdmin(admin.ModelAdmin):
    list_select_related = (
        'user__profile__state', 'user__profile__main_character', 'character')
    list_display = (
        user_profile_pic,
        user_username,
        user_main_organization,
        'character',
    )
    search_fields = (
        'user__username',
        'character__character_name',
        'character__corporation_name',
        'character__alliance_name',
        'character__faction_name'
    )
    list_filter = (
        MainCorporationsFilter,
        MainAllianceFilter,
    )

    class Media:
        css = {
            "all": ("allianceauth/authentication/css/admin.css",)
        }

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return 'owner_hash', 'character'
        return tuple()


@admin.register(OwnershipRecord)
class OwnershipRecordAdmin(BaseOwnershipAdmin):
    list_display = BaseOwnershipAdmin.list_display + ('created',)


@admin.register(CharacterOwnership)
class CharacterOwnershipAdmin(BaseOwnershipAdmin):
    def has_add_permission(self, request):
        return False


class PermissionAdmin(admin.ModelAdmin):
    actions = None
    readonly_fields = [field.name for field in BasePermission._meta.fields]
    search_fields = ('codename', )
    list_display = ('admin_name', 'name', 'codename', 'content_type')
    list_filter = ('content_type__app_label',)

    @staticmethod
    def admin_name(obj):
        return str(obj)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        # can see list but not edit it
        return not obj


# Hack to allow registration of django.contrib.auth models in our authentication app
class User(BaseUser):
    class Meta:
        proxy = True
        verbose_name = BaseUser._meta.verbose_name
        verbose_name_plural = BaseUser._meta.verbose_name_plural


class Permission(BasePermission):
    class Meta:
        proxy = True
        verbose_name = BasePermission._meta.verbose_name
        verbose_name_plural = BasePermission._meta.verbose_name_plural


try:
    admin.site.unregister(BaseUser)
finally:
    admin.site.register(User, UserAdmin)
    admin.site.register(Permission, PermissionAdmin)


@receiver(pre_save, sender=User)
def redirect_pre_save(sender, signal=None, *args, **kwargs):
    pre_save.send(BaseUser, *args, **kwargs)


@receiver(post_save, sender=User)
def redirect_post_save(sender, signal=None, *args, **kwargs):
    post_save.send(BaseUser, *args, **kwargs)


@receiver(pre_delete, sender=User)
def redirect_pre_delete(sender, signal=None, *args, **kwargs):
    pre_delete.send(BaseUser, *args, **kwargs)


@receiver(post_delete, sender=User)
def redirect_post_delete(sender, signal=None, *args, **kwargs):
    post_delete.send(BaseUser, *args, **kwargs)


@receiver(m2m_changed, sender=User.groups.through)
def redirect_m2m_changed_groups(sender, signal=None, *args, **kwargs):
    m2m_changed.send(BaseUser, *args, **kwargs)


@receiver(m2m_changed, sender=User.user_permissions.through)
def redirect_m2m_changed_permissions(sender, signal=None, *args, **kwargs):
    m2m_changed.send(BaseUser, *args, **kwargs)
