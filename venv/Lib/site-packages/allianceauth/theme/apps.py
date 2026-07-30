from django.apps import AppConfig


class ThemeConfig(AppConfig):
    name = "allianceauth.theme"
    label = "theme"

    def ready(self):
        pass
