"""Counters for Task Statistics."""

import datetime as dt
from typing import NamedTuple, Optional

from .event_series import EventSeries

# Global series for counting task events.
succeeded_tasks = EventSeries("SUCCEEDED_TASKS")
retried_tasks = EventSeries("RETRIED_TASKS")
failed_tasks = EventSeries("FAILED_TASKS")


class _TaskCounts(NamedTuple):
    succeeded: int
    retried: int
    failed: int
    total: int
    earliest_task: Optional[dt.datetime]
    hours: int


def dashboard_results(hours: int) -> _TaskCounts:
    """Counts of all task events within the given time frame."""

    def earliest_if_exists(events: EventSeries, earliest: dt.datetime) -> list:
        my_earliest = events.first_event(earliest=earliest)
        return [my_earliest] if my_earliest else []

    earliest = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    earliest_events = []
    succeeded_count = succeeded_tasks.count(earliest=earliest)
    earliest_events += earliest_if_exists(succeeded_tasks, earliest)
    retried_count = retried_tasks.count(earliest=earliest)
    earliest_events += earliest_if_exists(retried_tasks, earliest)
    failed_count = failed_tasks.count(earliest=earliest)
    earliest_events += earliest_if_exists(failed_tasks, earliest)
    return _TaskCounts(
        succeeded=succeeded_count,
        retried=retried_count,
        failed=failed_count,
        total=succeeded_count + retried_count + failed_count,
        earliest_task=min(earliest_events) if earliest_events else None,
        hours=hours,
    )
