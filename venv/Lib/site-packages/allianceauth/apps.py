from django.apps import AppConfig


class AllianceAuthConfig(AppConfig):
    name = 'allianceauth'

    def ready(self) -> None:
        import allianceauth.checks # noqa
