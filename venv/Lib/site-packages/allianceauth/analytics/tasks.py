import requests
import logging
from django.conf import settings
from django.apps import apps
from celery import shared_task
from .models import AnalyticsTokens, AnalyticsIdentifier
from .utils import (
    existence_baremetal_or_docker,
    install_stat_addons,
    install_stat_tokens,
    install_stat_users)

from allianceauth import __version__

logger = logging.getLogger(__name__)

BASE_URL = "https://www.google-analytics.com"

DEBUG_URL = f"{BASE_URL}/debug/mp/collect"
COLLECTION_URL = f"{BASE_URL}/mp/collect"

if getattr(settings, "ANALYTICS_ENABLE_DEBUG", False) and settings.DEBUG:
    # Force sending of analytics data during in a debug/test environment
    # Useful for developers working on this feature.
    logger.warning(
        "You have 'ANALYTICS_ENABLE_DEBUG' Enabled! "
        "This debug instance will send analytics data!")
    DEBUG_URL = COLLECTION_URL

ANALYTICS_URL = COLLECTION_URL

if settings.DEBUG is True:
    ANALYTICS_URL = DEBUG_URL


def analytics_event(namespace: str,
                    task: str,
                    label: str = "",
                    result: str = "",
                    value: int = 1,
                    event_type: str = 'Celery'):
    """
    Send a Google Analytics Event for each token stored
    Includes check for if its enabled/disabled

    Args:
        `namespace` (str): Celery Namespace
        `task` (str): Task Name
        `label` (str): Optional, additional task label
        `result` (str): Optional, Task Success/Exception
        `value` (int): Optional, If bulk, Query size, can be a Boolean
        `event_type` (str): Optional, Celery or Stats only, Default to Celery
    """
    for token in AnalyticsTokens.objects.filter(type='GA-V4'):
        if event_type == 'Stats':
            allowed = token.send_stats
        else:
            allowed = False

        if allowed is True:
            send_ga_tracking_celery_event.s(
                measurement_id=token.token,
                secret=token.secret,
                namespace=namespace,
                task=task,
                label=label,
                result=result,
                value=value).apply_async(priority=9)


@shared_task
def analytics_daily_stats() -> None:
    """Celery Task: Do not call directly

    Gathers a series of daily statistics
    Sends analytics events containing them
    """
    users = install_stat_users()
    tokens = install_stat_tokens()
    addons = install_stat_addons()
    existence_type = existence_baremetal_or_docker()
    logger.debug("Running Daily Analytics Upload")

    analytics_event(namespace='allianceauth.analytics',
                    task='send_install_stats',
                    label='existence',
                    value=1,
                    event_type='Stats')
    analytics_event(namespace='allianceauth.analytics',
                    task='send_install_stats',
                    label=existence_type,
                    value=1,
                    event_type='Stats')
    analytics_event(namespace='allianceauth.analytics',
                    task='send_install_stats',
                    label='users',
                    value=users,
                    event_type='Stats')
    analytics_event(namespace='allianceauth.analytics',
                    task='send_install_stats',
                    label='tokens',
                    value=tokens,
                    event_type='Stats')
    analytics_event(namespace='allianceauth.analytics',
                    task='send_install_stats',
                    label='addons',
                    value=addons,
                    event_type='Stats')
    for appconfig in apps.get_app_configs():
        if appconfig.label in [
            "django_celery_beat",
            "bootstrapform",
            "messages",
            "sessions",
            "auth",
            "staticfiles",
            "users",
            "addons",
            "admin",
            "humanize",
            "contenttypes",
            "sortedm2m",
            "django_bootstrap5",
            "tokens",
            "authentication",
            "services",
            "framework",
            "notifications"
            "eveonline",
            "navhelper",
            "analytics",
            "menu",
            "theme"
        ]:
            pass
        else:
            analytics_event(namespace='allianceauth.analytics',
                            task='send_extension_stats',
                            label=appconfig.label,
                            value=1,
                            event_type='Stats')


@shared_task
def send_ga_tracking_celery_event(
        measurement_id: str,
        secret: str,
        namespace: str,
        task: str,
        label: str = "",
        result: str = "",
        value: int = 1):
    """Celery Task: Do not call directly

    Sends an events to GA

    Parameters
    ----------
    `measurement_id` (str): GA Token
    `secret` (str): GA Authentication Secret
    `namespace` (str): Celery Namespace
    `task` (str): Task Name
    `label` (str): Optional, additional task label
    `result` (str): Optional, Task Success/Exception
    `value` (int): Optional, If bulk, Query size, can be a binary True/False
    """

    parameters = {
        'measurement_id': measurement_id,
        'api_secret': secret
    }

    payload = {
        'client_id': AnalyticsIdentifier.get_solo().identifier.hex,
        "user_properties": {
            "allianceauth_version": {
                "value": __version__
            }
        },
        'non_personalized_ads': True,
        "events": [{
            "name": "celery_event",
            "params": {
                    "namespace": namespace,
                    "task": task,
                    'result': result,
                    'label': label,
                    "value": value
            }
        }]
    }
    try:
        response = requests.post(
            ANALYTICS_URL,
            params=parameters,
            json=payload,
            timeout=10)
        response.raise_for_status()
        logger.debug(
            f"Analytics Celery/Stats Event HTTP{response.status_code}")
        return response.status_code
    except requests.exceptions.HTTPError as e:
        logger.debug(e)
        return response.status_code
    except requests.exceptions.ConnectionError as e:
        logger.debug(e)
        return "Failed"
