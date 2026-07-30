from django.contrib import admin

from .models import DiscourseUser
from ...admin import ServicesUserAdmin


@admin.register(DiscourseUser)
class DiscourseUserAdmin(ServicesUserAdmin):
    list_display = ServicesUserAdmin.list_display + (
        'enabled',
    )
