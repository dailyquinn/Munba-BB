from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "_main", "_state", "title", "level", "viewed")
    list_select_related = ("user", "user__profile__main_character", "user__profile__state")
    list_filter = (
        "level",
        "timestamp",
        "user__profile__state",
        ('user__profile__main_character', admin.RelatedOnlyFieldListFilter),
    )
    ordering = ("-timestamp", )
    search_fields = ["user__username", "user__profile__main_character__character_name"]

    @admin.display(
        ordering="user__profile__main_character__character_name"
    )
    def _main(self, obj):
        try:
            return obj.user.profile.main_character
        except AttributeError:
            return obj.user


    @admin.display(
        ordering="user__profile__state__name"
    )
    def _state(self, obj):
        return obj.user.profile.state


    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request) -> bool:
        return False
