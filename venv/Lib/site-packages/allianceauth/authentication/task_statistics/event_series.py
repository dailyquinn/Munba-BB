"""Event series for Task Statistics."""

import datetime as dt
import logging
from typing import List, Optional

from pytz import utc
from redis import Redis

from .helpers import get_redis_client_or_stub

logger = logging.getLogger(__name__)


class EventSeries:
    """API for recording and analyzing a series of events."""

    _ROOT_KEY = "ALLIANCEAUTH_EVENT_SERIES"

    def __init__(self, key_id: str, redis: Optional[Redis] = None) -> None:
        self._redis = get_redis_client_or_stub() if not redis else redis
        self._key_id = str(key_id)
        self.clear()

    @property
    def is_disabled(self):
        """True when this object is disabled, e.g. Redis was not available at startup."""
        return hasattr(self._redis, "IS_STUB")

    @property
    def _key_counter(self):
        return f"{self._ROOT_KEY}_{self._key_id}_COUNTER"

    @property
    def _key_sorted_set(self):
        return f"{self._ROOT_KEY}_{self._key_id}_SORTED_SET"

    def add(self, event_time: dt.datetime = None) -> None:
        """Add event.

        Args:
        - event_time: timestamp of event. Will use current time if not specified.
        """
        if not event_time:
            event_time = dt.datetime.now(dt.timezone.utc)
        my_id = self._redis.incr(self._key_counter)
        self._redis.zadd(self._key_sorted_set, {my_id: event_time.timestamp()})

    def all(self) -> List[dt.datetime]:
        """List of all known events."""
        return [
            event[1]
            for event in self._redis.zrangebyscore(
                self._key_sorted_set,
                "-inf",
                "+inf",
                withscores=True,
                score_cast_func=self._cast_scores_to_dt,
            )
        ]

    def clear(self) -> None:
        """Clear all events."""
        self._redis.delete(self._key_sorted_set)
        self._redis.delete(self._key_counter)

    def count(self, earliest: dt.datetime = None, latest: dt.datetime = None) -> int:
        """Count of events, can be restricted to given time frame.

        Args:
        - earliest: Date of first events to count(inclusive), or -infinite if not specified
        - latest: Date of last events to count(inclusive), or +infinite if not specified
        """
        minimum = "-inf" if not earliest else earliest.timestamp()
        maximum = "+inf" if not latest else latest.timestamp()
        return self._redis.zcount(self._key_sorted_set, min=minimum, max=maximum)

    def first_event(self, earliest: dt.datetime = None) -> Optional[dt.datetime]:
        """Date/Time of first event. Returns `None` if series has no events.

        Args:
        - earliest: Date of first events to count(inclusive), or any if not specified
        """
        minimum = "-inf" if not earliest else earliest.timestamp()
        event = self._redis.zrangebyscore(
            self._key_sorted_set,
            minimum,
            "+inf",
            withscores=True,
            start=0,
            num=1,
            score_cast_func=self._cast_scores_to_dt,
        )
        if not event:
            return None
        return event[0][1]

    @staticmethod
    def _cast_scores_to_dt(score) -> dt.datetime:
        return dt.datetime.fromtimestamp(float(score), tz=utc)
