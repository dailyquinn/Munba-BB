"""Signals for Task Statistics."""

from celery.signals import (
    task_failure, task_internal_error, task_retry, task_success, worker_ready,
)

from django.conf import settings

from .counters import failed_tasks, retried_tasks, succeeded_tasks


def reset_counters():
    """Reset all counters for the celery status."""
    succeeded_tasks.clear()
    failed_tasks.clear()
    retried_tasks.clear()


def is_enabled() -> bool:
    """Return True if task statistics are enabled, else return False."""
    return not bool(
        getattr(settings, "ALLIANCEAUTH_DASHBOARD_TASK_STATISTICS_DISABLED", False)
    )


@worker_ready.connect
def reset_counters_when_celery_restarted(*args, **kwargs):
    if is_enabled():
        reset_counters()


@task_success.connect
def record_task_succeeded(*args, **kwargs):
    if is_enabled():
        succeeded_tasks.add()


@task_retry.connect
def record_task_retried(*args, **kwargs):
    if is_enabled():
        retried_tasks.add()


@task_failure.connect
def record_task_failed(*args, **kwargs):
    if is_enabled():
        failed_tasks.add()


@task_internal_error.connect
def record_task_internal_error(*args, **kwargs):
    if is_enabled():
        failed_tasks.add()
