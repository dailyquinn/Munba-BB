from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import CallbackRedirect, Scope, Token

admin.site.register(CallbackRedirect)


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'help_text')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    def get_queryset(self, request) -> QuerySet["Token"]:
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('scopes')

    @admin.display(
        description='Scopes'
    )
    def get_scopes(self, obj) -> str:
        return ", ".join([x.name for x in obj.scopes.all()])

    User = get_user_model()
    list_display = ('user', 'character_name', 'get_scopes')
    search_fields = ['user__%s' % User.USERNAME_FIELD, 'character_name', 'scopes__name']
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        'character_name'
    )
    ordering = ('user',)
    readonly_fields = (
        'character_id',
        'character_name',
        'token_type',
        'character_owner_hash',
        'scopes',
        'sso_version'
    )
