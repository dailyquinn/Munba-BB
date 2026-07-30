from django.contrib import admin

from .models import AnalyticsIdentifier, AnalyticsTokens
from solo.admin import SingletonModelAdmin


@admin.register(AnalyticsIdentifier)
class AnalyticsIdentifierAdmin(SingletonModelAdmin):
    search_fields = ['identifier', ]
    list_display = ['identifier', ]


@admin.register(AnalyticsTokens)
class AnalyticsTokensAdmin(admin.ModelAdmin):
    search_fields = ['name', ]
    list_display = ['name', 'type', ]
