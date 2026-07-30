"""Templatetags for notifications

These template tags are required to enable the notifications refresh functionality
in the browser.
"""

import logging

from django import template
from django.conf import settings
from django.contrib.auth.models import User

from allianceauth.notifications.models import Notification


logger = logging.getLogger(__name__)
register = template.Library()


@register.filter
def user_unread_notification_count(user: object) -> int:
    """returns the number of unread notifications for user

    Will return -1 on error
    """
    if not isinstance(user, User):
        unread_count = -1
    else:
        unread_count = Notification.objects.user_unread_count(user.pk)

    return unread_count


@register.simple_tag
def notifications_refresh_time() -> int:
    refresh_time = getattr(settings, 'NOTIFICATIONS_REFRESH_TIME', Notification.NOTIFICATIONS_REFRESH_TIME_DEFAULT)
    if (not isinstance(refresh_time, int) or refresh_time < 0):
        logger.warning('NOTIFICATIONS_REFRESH_TIME setting is invalid. Using default.')
        refresh_time = Notification.NOTIFICATIONS_REFRESH_TIME_DEFAULT

    return refresh_time
