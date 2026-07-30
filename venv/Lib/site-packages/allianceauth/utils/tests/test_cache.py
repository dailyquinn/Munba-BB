from unittest.mock import MagicMock, patch

from django.test import TestCase

from allianceauth.utils.cache import get_redis_client

MODULE_PATH = "allianceauth.utils.cache"


class RedisClientStub:
    """Substitute for a Redis client."""

    pass


class TestGetRedisClient(TestCase):
    def test_should_work_with_aa2_api(self):
        # given
        mock_django_cache = MagicMock()
        mock_django_cache.get_master_client.return_value = RedisClientStub()
        # when
        with patch(MODULE_PATH + ".django_redis", None), patch.dict(
            MODULE_PATH + ".caches", {"default": mock_django_cache}
        ):
            client = get_redis_client()
        # then
        self.assertIsInstance(client, RedisClientStub)

    def test_should_work_with_aa3_api(self):
        # given
        mock_django_redis = MagicMock()
        mock_django_redis.get_redis_connection.return_value = RedisClientStub()
        # when
        with patch(MODULE_PATH + ".django_redis", mock_django_redis), patch.dict(
            MODULE_PATH + ".caches", {"default": None}
        ):
            client = get_redis_client()
        # then
        self.assertIsInstance(client, RedisClientStub)
