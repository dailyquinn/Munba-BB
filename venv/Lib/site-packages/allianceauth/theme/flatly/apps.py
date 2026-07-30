from django.apps import AppConfig


class FlatlyThemeConfig(AppConfig):
    name = "allianceauth.theme.flatly"
    label = "flatly"
    version = "5.3.3"
    verbose_name = f"Bootswatch Flatly v{version}"

    def ready(self):
        pass
