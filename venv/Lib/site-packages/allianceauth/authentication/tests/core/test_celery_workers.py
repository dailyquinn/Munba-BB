from unittest.mock import patch

from amqp.exceptions import ChannelError

from django.test import TestCase

from allianceauth.authentication.core.celery_workers import (
    active_tasks_count, queued_tasks_count,
)

MODULE_PATH = "allianceauth.authentication.core.celery_workers"


@patch(MODULE_PATH + ".current_app")
class TestActiveTasksCount(TestCase):
    def test_should_return_correct_count_when_no_active_tasks(self, mock_current_app):
        # given
        mock_current_app.control.inspect.return_value.active.return_value = {
            "queue": []
        }
        # when
        result = active_tasks_count()
        # then
        self.assertEqual(result, 0)

    def test_should_return_correct_task_count_for_active_tasks(self, mock_current_app):
        # given
        mock_current_app.control.inspect.return_value.active.return_value = {
            "queue": [1, 2, 3]
        }
        # when
        result = active_tasks_count()
        # then
        self.assertEqual(result, 3)

    def test_should_return_correct_task_count_for_multiple_queues(
        self, mock_current_app
    ):
        # given
        mock_current_app.control.inspect.return_value.active.return_value = {
            "queue_1": [1, 2],
            "queue_2": [3, 4],
        }
        # when
        result = active_tasks_count()
        # then
        self.assertEqual(result, 4)

    def test_should_return_none_when_celery_not_available(self, mock_current_app):
        # given
        mock_current_app.control.inspect.return_value.active.return_value = None
        # when
        result = active_tasks_count()
        # then
        self.assertIsNone(result)


@patch(MODULE_PATH + ".current_app")
class TestQueuedTasksCount(TestCase):
    def test_should_return_queue_length_when_queue_exists(self, mock_current_app):
        # given
        mock_conn = (
            mock_current_app.connection_or_acquire.return_value.__enter__.return_value
        )
        mock_conn.default_channel.queue_declare.return_value.message_count = 7
        # when
        result = queued_tasks_count()
        # then
        self.assertEqual(result, 7)

    def test_should_return_0_when_queue_does_not_exists(self, mock_current_app):
        # given
        mock_current_app.connection_or_acquire.side_effect = ChannelError
        # when
        result = queued_tasks_count()
        # then
        self.assertEqual(result, 0)

    def test_should_return_None_on_other_errors(self, mock_current_app):
        # given
        mock_current_app.connection_or_acquire.side_effect = RuntimeError
        # when
        result = queued_tasks_count()
        # then
        self.assertIsNone(result)
