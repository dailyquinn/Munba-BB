import logging
import time
from django.core.cache import cache
from esi.exceptions import ESIBucketLimitException

logger = logging.getLogger(__name__)

seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def interval_to_seconds(s):
    return int(s[:-1]) * seconds_per_unit[s[-1]]


class ESIRateLimitBucket:
    MARKET_DATA_HISTORY = ("market_data_history", 300, 60)
    CHARACTER_CORPORATION_HISTORY = ("character_corporation_history", 300, 60)

    def __init__(self, slug, limit, window):
        self.slug = slug
        self.limit = limit
        self.window = window

    @classmethod
    def choices(cls):
        return [(bucket.slug, bucket.slug.replace("_", " ").title()) for bucket in cls]

    def __str__(self):
        return f"Rate Limit: {self.slug} - {self.limit} in {self.window}Seconds"


class ESIRateLimiter:
    def __init__(self) -> None:
        pass

    def _slug_to_key(self, slug) -> str:
        return f"esi:bucket:{slug}"

    def init_bucket(self, bucket: ESIRateLimitBucket) -> None:
        # Set our bucket up if it doesn't already exist
        cache.set(
            self._slug_to_key(bucket.slug),
            bucket.limit,
            timeout=bucket.window,
            nx=True  # Don't re-create if it does exist
        )

    def get_bucket(self, bucket: ESIRateLimitBucket) -> int:
        # get the value from the bucket
        return int(
            cache.get(
                self._slug_to_key(bucket.slug),
                1  # When not found return 1
            )
        )

    def get_timeout(self, bucket: ESIRateLimitBucket) -> int:
        current_bucket = self.get_bucket(bucket)
        if current_bucket <= 0:
            timeout = cache.ttl(self._slug_to_key(bucket.slug)) + 1
            msg = (
                f"Rate limit for bucket '{bucket.slug}' exceeded: "
                f"{current_bucket}/{bucket.limit} in last {bucket.window}s. "
                f"Wait {timeout}s."
            )
            logger.warning(msg)
            return timeout  # return the time left till reset
        else:
            return 0  # we are good.

    def decr_bucket(self, bucket: ESIRateLimitBucket, delta: int = 1) -> int:
        # decrease the bucket value by <delta> from the bucket
        return cache.decr(
            self._slug_to_key(bucket.slug),
            delta
        )

    def set_bucket(self, bucket: ESIRateLimitBucket, new_limit: int = 1) -> int:
        # decrease the bucket value by <delta> from the bucket
        return cache.set(
            self._slug_to_key(bucket.slug),
            int(new_limit),
            timeout=bucket.window
        )

    def check_bucket(self, bucket: ESIRateLimitBucket):
        self.init_bucket(bucket)
        # get the value
        bucket_val = self.get_bucket(bucket)
        if bucket_val <= 0:
            timeout = self.get_timeout(bucket)
            if timeout > 0:
                raise ESIBucketLimitException(bucket, timeout)
            return

    def check_decr_bucket(self, bucket: ESIRateLimitBucket, raise_on_limit: bool = True):
        try:
            self.check_bucket(bucket)
            self.decr_bucket(bucket)
        except ESIBucketLimitException as ex:
            if raise_on_limit:
                raise ex
            else:
                time.sleep(ex.reset)


ESIRateLimits = ESIRateLimiter()
