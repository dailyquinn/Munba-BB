from django.contrib import admin

from .models import XenforoUser
from ...admin import ServicesUserAdmin


@admin.register(XenforoUser)
class XenforoUserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + ('username',)
    search_fields = ServicesUserAdmin.search_fields + ('username', )
