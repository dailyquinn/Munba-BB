from typing import List, Iterable, Callable

from django.urls import include
import esi.urls
from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, include, path
from django.views.generic.base import TemplateView

import allianceauth.authentication.urls
import allianceauth.authentication.views
import allianceauth.groupmanagement.urls
import allianceauth.notifications.urls
import allianceauth.services.urls
from allianceauth import NAME, views
from allianceauth.authentication import hmac_urls
from allianceauth.authentication.decorators import (
    decorate_url_patterns,
    main_character_required
)
from allianceauth.hooks import get_hooks

admin.site.site_header = NAME


def urls_from_apps(
    apps_hook_functions: Iterable[Callable], public_views_allowed: List[str]
) -> List[URLPattern]:
    """Return urls from apps and add default decorators."""

    url_patterns = []
    allowed_apps = set(public_views_allowed)
    for app_hook_function in apps_hook_functions:
        url_hook = app_hook_function()
        app_pattern = url_hook.include_pattern
        excluded_views = (
            url_hook.excluded_views
            if app_pattern.app_name in allowed_apps
            else None
        )
        url_patterns += [
            path(
                "",
                decorate_url_patterns(
                    [app_pattern], main_character_required, excluded_views
                )
            )
        ]

    return url_patterns


# Functional/Untranslated URL's
urlpatterns = [
    # Locale
    path('i18n/', include('django.conf.urls.i18n')),

    # Authentication
    path('', include(allianceauth.authentication.urls)),
    path('account/login/', TemplateView.as_view(template_name='public/login.html'), name='auth_login_user'),
    path('account/', include(hmac_urls)),

    # Admin urls
    path('admin/', admin.site.urls),

    # SSO
    path('sso/', include((esi.urls, 'esi'), namespace='esi')),
    path('sso/login', allianceauth.authentication.views.sso_login, name='auth_sso_login'),

    # Notifications
    path('', include(allianceauth.notifications.urls)),

    # Groups
    path('', include(allianceauth.groupmanagement.urls)),

    # Services
    path('', decorate_url_patterns(allianceauth.services.urls.urlpatterns, main_character_required)),

    # Night mode
    path('night/', views.NightModeRedirectView.as_view(), name='nightmode'),

    # Theme Change
    path('theme/', views.ThemeRedirectView.as_view(), name='theme'),

    # Minimize Menu
    path('minimize-sidebar/', views.MinimizeSidebarRedirectView.as_view(), name='minimize_sidebar')
]

url_hooks = get_hooks("url_hook")
public_views_allows = getattr(settings, "APPS_WITH_PUBLIC_VIEWS", [])
urlpatterns += urls_from_apps(url_hooks, public_views_allows)
