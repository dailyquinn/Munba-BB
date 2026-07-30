"""Helpers for Task Statistics."""

import logging

from redis import Redis, RedisError

from allianceauth.utils.cache import get_redis_client

logger = logging.getLogger(__name__)


class _RedisStub:
    """Stub of a Redis client.

    It's purpose is to prevent EventSeries objects from trying to access Redis
    when it is not available. e.g. when the Sphinx docs are rendered by readthedocs.org.
    """

    IS_STUB = True

    def delete(self, *args, **kwargs):
        pass

    def incr(self, *args, **kwargs):
        return 0

    def zadd(self, *args, **kwargs):
        pass

    def zcount(self, *args, **kwargs):
        pass

    def zrangebyscore(self, *args, **kwargs):
        pass


def get_redis_client_or_stub() -> Redis:
    """Return AA's default cache client or a stub if Redis is not available."""
    redis = get_redis_client()
    try:
        if not redis.ping():
            raise RuntimeError()
    except (AttributeError, RedisError, RuntimeError):
        logger.exception(
            "Failed to establish a connection with Redis. "
            "This EventSeries object is disabled.",
        )
        return _RedisStub()
    return redis
