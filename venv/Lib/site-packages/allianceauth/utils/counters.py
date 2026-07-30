"""Counters."""

from typing import Optional

from redis import Redis

from django.core.cache import cache

from .cache import get_redis_client


class ItemCounter:
    """A process safe item counter.

    Args:
        - name: Unique name for the counter
        - minimum: Counter can not go below the minimum, when set
        - redis: A Redis client. Will use AA's cache client by default
    """

    CACHE_KEY_BASE = "allianceauth-item-counter"
    DEFAULT_CACHE_TIMEOUT = 24 * 3600

    def __init__(
        self, name: str, minimum: Optional[int] = None, redis: Optional[Redis] = None
    ) -> None:
        if not name:
            raise ValueError("Must define a name")

        self._name = str(name)
        self._minimum = minimum
        self._redis = get_redis_client() if not redis else redis

    @property
    def _cache_key(self) -> str:
        return f"{self.CACHE_KEY_BASE}-{self._name}"

    def reset(self, init_value: int = 0):
        """Reset counter to initial value."""
        with self._redis.lock(f"{self.CACHE_KEY_BASE}-reset"):
            if self._minimum is not None and init_value < self._minimum:
                raise ValueError("Can not reset below minimum")

            cache.set(self._cache_key, init_value, self.DEFAULT_CACHE_TIMEOUT)

    def incr(self, delta: int = 1):
        """Increment counter by delta."""
        try:
            cache.incr(self._cache_key, delta)
        except ValueError:
            pass

    def decr(self, delta: int = 1):
        """Decrement counter by delta."""
        with self._redis.lock(f"{self.CACHE_KEY_BASE}-decr"):
            if self._minimum is not None and self.value() == self._minimum:
                return
            try:
                cache.decr(self._cache_key, delta)
            except ValueError:
                pass

    def value(self) -> Optional[int]:
        """Return current value or None if not yet initialized."""
        return cache.get(self._cache_key)
