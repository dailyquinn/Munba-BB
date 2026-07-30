from django.conf import settings
from .views import NightModeRedirectView


def auth_settings(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_URL': settings.SITE_URL,
        'NIGHT_MODE': NightModeRedirectView.night_mode_state(request),
    }
