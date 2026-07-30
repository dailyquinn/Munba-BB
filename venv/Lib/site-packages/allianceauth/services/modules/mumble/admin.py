from django.contrib import admin

from .models import MumbleUser
from ...admin import ServicesUserAdmin


@admin.register(MumbleUser)
class MumbleUserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + (
        'username',
        'groups',
    )
    search_fields = ServicesUserAdmin.search_fields + (
        'username',
        'groups'
    )

    fields = ('user', 'username', 'groups')  # pwhash is hidden from admin panel
