from redis import Redis

from django.core.cache import caches

try:
    import django_redis
except ImportError:
    django_redis = None


def get_redis_client() -> Redis:
    """Get the configured redis client used by Django for caching.

    This function is a wrapper designed to work for both AA2 and AA3
    and should always be used to ensure backwards compatibility.
    """
    try:
        return django_redis.get_redis_connection("default")
    except AttributeError:
        default_cache = caches["default"]
        return default_cache.get_master_client()
