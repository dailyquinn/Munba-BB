from django.contrib import admin

from .models import OpenfireUser
from ...admin import ServicesUserAdmin


@admin.register(OpenfireUser)
class OpenfireUserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + ('username',)
    search_fields = ServicesUserAdmin.search_fields + ('username', )
