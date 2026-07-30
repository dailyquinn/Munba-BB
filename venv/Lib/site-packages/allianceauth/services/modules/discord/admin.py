import logging

from django.contrib import admin

from ...admin import ServicesUserAdmin
from . import __title__
from .models import DiscordUser
from .utils import LoggerAddTag
from .auth_hooks import DiscordService

logger = LoggerAddTag(logging.getLogger(__name__), __title__)


@admin.register(DiscordUser)
class DiscordUserAdmin(ServicesUserAdmin):
    search_fields = ServicesUserAdmin.search_fields + ('uid', 'username')
    list_display = ServicesUserAdmin.list_display + ('activated', '_username', '_uid')
    list_filter = ServicesUserAdmin.list_filter + ('activated',)
    ordering = ('-activated',)

    def delete_queryset(self, request, queryset):
        for user in queryset:
            user.delete_user()

    @admin.display(description='Discord ID (UID)', ordering='uid')
    def _uid(self, obj):
        return obj.uid

    @admin.display(description='Discord Username', ordering='username')
    def _username(self, obj):
        return DiscordService.get_discord_username(
            username=obj.username, discriminator=obj.discriminator
        )
