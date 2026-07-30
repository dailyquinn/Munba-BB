"""API for interacting with celery workers."""

import itertools
import logging
from typing import Optional

from amqp.exceptions import ChannelError
from celery import current_app

from django.conf import settings

logger = logging.getLogger(__name__)


def active_tasks_count() -> Optional[int]:
    """Return count of currently active tasks
    or None if celery workers are not online.
    """
    inspect = current_app.control.inspect()
    return _tasks_count(inspect.active())


def _tasks_count(data: dict) -> Optional[int]:
    """Return count of tasks in data from celery inspect API."""
    try:
        tasks = itertools.chain(*data.values())
    except AttributeError:
        return None
    return len(list(tasks))


def queued_tasks_count() -> Optional[int]:
    """Return count of queued tasks. Return None if there was an error."""
    try:
        with current_app.connection_or_acquire() as conn:
            result = conn.default_channel.queue_declare(
                queue=getattr(settings, "CELERY_DEFAULT_QUEUE", "celery"), passive=True
            )
            return result.message_count

    except ChannelError:
        # Queue doesn't exist, probably empty
        return 0

    except Exception:
        logger.exception("Failed to get celery queue length")

    return None
