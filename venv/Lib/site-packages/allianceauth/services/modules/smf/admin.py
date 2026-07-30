from django.contrib import admin

from .models import SmfUser
from ...admin import ServicesUserAdmin


@admin.register(SmfUser)
class SmfUserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + ('username',)
    search_fields = ServicesUserAdmin.search_fields + ('username', )
