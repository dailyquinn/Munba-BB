from unittest import TestCase
from unittest.mock import patch

from redis import RedisError

from allianceauth.authentication.task_statistics.helpers import (
    _RedisStub, get_redis_client_or_stub,
)

MODULE_PATH = "allianceauth.authentication.task_statistics.helpers"


class TestGetRedisClient(TestCase):
    def test_should_return_mock_if_redis_not_available_1(self):
        # when
        with patch(MODULE_PATH + ".get_redis_client") as mock_get_master_client:
            mock_get_master_client.return_value.ping.side_effect = RedisError
            result = get_redis_client_or_stub()
        # then
        self.assertIsInstance(result, _RedisStub)

    def test_should_return_mock_if_redis_not_available_2(self):
        # when
        with patch(MODULE_PATH + ".get_redis_client") as mock_get_master_client:
            mock_get_master_client.return_value.ping.return_value = False
            result = get_redis_client_or_stub()
        # then
        self.assertIsInstance(result, _RedisStub)
