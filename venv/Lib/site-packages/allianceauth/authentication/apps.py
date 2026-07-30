from django.apps import AppConfig
from django.core.checks import register, Tags
from django.utils.translation import gettext_lazy as _


class AuthenticationConfig(AppConfig):
    name = "allianceauth.authentication"
    label = "authentication"
    verbose_name = _("Authentication")

    def ready(self):
        from allianceauth.authentication import checks, signals  # noqa: F401
        from allianceauth.authentication.task_statistics import (
            signals as celery_signals,
        )

        register(Tags.security)(checks.check_login_scopes_setting)
        celery_signals.reset_counters()
