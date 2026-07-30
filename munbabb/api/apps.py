from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # We can start the APScheduler here or similar.
        # But we must ensure it only runs once and not in management commands.
        pass
