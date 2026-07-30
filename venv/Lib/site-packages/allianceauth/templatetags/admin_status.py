import logging

import requests
from packaging.version import InvalidVersion, Version as Pep440Version

from django import template
from django.conf import settings
from django.core.cache import cache

from allianceauth import __version__
from allianceauth.authentication.task_statistics.counters import (
    dashboard_results,
)

register = template.Library()

# cache timers
TAG_CACHE_TIME = 3600  # 1 hours
NOTIFICATION_CACHE_TIME = 300  # 5 minutes
# timeout for all requests
REQUESTS_TIMEOUT = 5    # 5 seconds
# max pages to be fetched from gitlab
MAX_PAGES = 50

GITLAB_AUTH_REPOSITORY_TAGS_URL = (
    'https://gitlab.com/api/v4/projects/allianceauth%2Fallianceauth/repository/tags'
)
GITLAB_AUTH_ANNOUNCEMENT_ISSUES_URL = (
    'https://gitlab.com/api/v4/projects/allianceauth%2Fallianceauth/issues'
    '?labels=announcement&state=opened'
)

logger = logging.getLogger(__name__)


@register.simple_tag()
def decimal_widthratio(this_value, max_value, max_width) -> str:
    if max_value == 0:
        return str(0)

    return str(round(this_value / max_value * max_width, 2))


@register.inclusion_tag('allianceauth/admin-status/overview.html')
def status_overview() -> dict:
    response = {
        "notifications": list(),
        "current_version": __version__,
        "tasks_succeeded": 0,
        "tasks_retried": 0,
        "tasks_failed": 0,
        "tasks_total": 0,
        "tasks_hours": 0,
        "earliest_task": None,
        "debug": settings.DEBUG if settings.DISPLAY_DEBUG else False,
    }
    response.update(_current_notifications())
    response.update(_current_version_summary())
    response.update(_celery_stats())
    return response


def _celery_stats() -> dict:
    hours = getattr(settings, "ALLIANCEAUTH_DASHBOARD_TASKS_MAX_HOURS", 24)
    results = dashboard_results(hours=hours)
    return {
        "tasks_succeeded": results.succeeded,
        "tasks_retried": results.retried,
        "tasks_failed": results.failed,
        "tasks_total": results.total,
        "tasks_hours": results.hours,
        "earliest_task": results.earliest_task,
    }


def _current_notifications() -> dict:
    """returns the newest 5 announcement issues"""
    try:
        notifications = cache.get_or_set(
            'gitlab_notification_issues',
            _fetch_notification_issues_from_gitlab,
            NOTIFICATION_CACHE_TIME
        )
    except requests.HTTPError:
        logger.warning('Error while getting gitlab notifications', exc_info=True)
        top_notifications = []
    else:
        if notifications:
            top_notifications = notifications[:5]
        else:
            top_notifications = []

    response = {
        'notifications': top_notifications,
    }
    return response


def _fetch_notification_issues_from_gitlab() -> list:
    return _fetch_list_from_gitlab(GITLAB_AUTH_ANNOUNCEMENT_ISSUES_URL, max_pages=10)


def _current_version_summary() -> dict:
    """returns the current version info"""
    try:
        tags = cache.get_or_set(
            'git_release_tags', _fetch_tags_from_gitlab, TAG_CACHE_TIME
        )
    except requests.HTTPError:
        logger.warning('Error while getting gitlab release tags', exc_info=True)
        return {}

    if not tags:
        return {}

    (
        latest_patch_version,
        latest_beta_version
    ) = _latests_versions(tags)
    current_version = Pep440Version(__version__)

    has_latest_patch = \
        current_version >= latest_patch_version if latest_patch_version else False
    has_current_beta = \
        current_version <= latest_beta_version \
        and latest_patch_version <= latest_beta_version \
        if latest_beta_version else False

    response = {
        'latest_patch': has_latest_patch,
        'latest_beta': has_current_beta,
        'current_version': str(current_version),
        'latest_patch_version': str(latest_patch_version),
        'latest_beta_version': str(latest_beta_version)
    }
    return response


def _fetch_tags_from_gitlab():
    return _fetch_list_from_gitlab(GITLAB_AUTH_REPOSITORY_TAGS_URL)


def _latests_versions(tags: list) -> tuple:
    """returns latests version from given tags list

    Non-compliant tags will be ignored
    """
    versions = list()
    betas = list()
    for tag in tags:
        try:
            version = Pep440Version(tag.get('name'))
        except InvalidVersion:
            pass
        else:
            if version.is_prerelease or version.is_devrelease:
                betas.append(version)
            else:
                versions.append(version)

    latest_patch_version = max(versions)
    latest_beta_version = max(betas)
    return (
        latest_patch_version,
        latest_beta_version
    )


def _fetch_list_from_gitlab(url: str, max_pages: int = MAX_PAGES) -> list:
    """returns a list from the GitLab API. Supports paging"""
    result = list()

    for page in range(1, max_pages + 1):
        try:
            request = requests.get(
                url, params={'page': page}, timeout=REQUESTS_TIMEOUT
            )
            request.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_str = str(e)

            logger.warning(
                f'Unable to fetch from GitLab API. Error: {error_str}',
                exc_info=True,
            )

            return result

        result += request.json()

        if 'x-total-pages' in request.headers:
            try:
                total_pages = int(request.headers['x-total-pages'])
            except ValueError:
                total_pages = None
        else:
            total_pages = None

        if not total_pages or page >= total_pages:
            break

    return result
