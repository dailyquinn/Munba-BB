from django.apps import AppConfig


class BootstrapThemeConfig(AppConfig):
    name = "allianceauth.theme.bootstrap"
    label = "bootstrap"
    version = "5.3.3"
    verbose_name = f"Bootstrap v{version}"

    def ready(self):
        pass
