from django.apps import AppConfig


class DarklyThemeConfig(AppConfig):
    name = "allianceauth.theme.darkly"
    label = "darkly"
    version = "5.3.3"
    verbose_name = f"Bootswatch Darkly v{version}"

    def ready(self):
        pass
