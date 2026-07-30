from django.contrib import admin
from .models import Ips4User


@admin.register(Ips4User)
class Ips4UserAdmin(admin.ModelAdmin):
        list_display = ('user', 'username', 'id')
        search_fields = ('user__username', 'username', 'id')
