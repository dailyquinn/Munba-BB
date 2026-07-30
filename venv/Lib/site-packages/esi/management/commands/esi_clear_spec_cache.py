from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Clear ESI OpenAPI specification document caches.'

    def handle(self, *args, **options):
        self.stdout.write("Finding all ESI Spec Caches.")
        try:
            from django_redis import get_redis_connection
            _client = get_redis_connection("default")
        except (NotImplementedError, ModuleNotFoundError):
            from django.core.cache import caches
            default_cache = caches['default']
            _client = default_cache.get_master_client()

        keys = _client.keys(":?:ESI_API_CACHE_*")
        self.stdout.write(f"Found {len(keys)} cached entries")

        if keys:
            deleted = _client.delete(*keys)
            self.stdout.write(f"Deleted {deleted} entries")
