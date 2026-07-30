import logging

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class NotificationQuerySet(models.QuerySet):
    """Custom QuerySet for Notification model"""

    def update(self, *args, **kwargs):
        """Override update to ensure cache is invalidated on very call."""
        super().update(*args, **kwargs)
        user_pks = set(self.select_related("user").values_list('user__pk', flat=True))
        for user_pk in user_pks:
            NotificationManager.invalidate_user_notification_cache(user_pk)


class NotificationManager(models.Manager):

    USER_NOTIFICATION_COUNT_PREFIX = 'USER_NOTIFICATION_COUNT'
    USER_NOTIFICATION_COUNT_CACHE_DURATION = 86_400

    def get_queryset(self):
        return NotificationQuerySet(self.model, using=self._db)

    def notify_user(
        self, user: object, title: str, message: str = None, level: str = 'info'
    ) -> object:
        """Sends a new notification to user. Returns newly created notification object.
        """
        max_notifications = self._max_notifications_per_user()
        if self.filter(user=user).count() >= max_notifications:
            to_be_deleted_qs = self.filter(user=user).order_by(
                "-timestamp"
            )[max_notifications - 1:]
            for notification in to_be_deleted_qs:
                notification.delete()

        if not message:
            message = title

        if level not in self.model.Level:
            level = self.model.Level.INFO
        obj = self.create(user=user, title=title, message=message, level=level)
        logger.info("Created notification %s", obj)
        return obj

    def _max_notifications_per_user(self) -> int:
        """Maximum number of notifications allowed per user."""
        max_notifications = getattr(
            settings,
            "NOTIFICATIONS_MAX_PER_USER",
            self.model.NOTIFICATIONS_MAX_PER_USER_DEFAULT
        )
        try:
            max_notifications = int(max_notifications)
        except ValueError:
            max_notifications = None
        if max_notifications is None or max_notifications < 0:
            logger.warning(
                "NOTIFICATIONS_MAX_PER_USER setting is invalid. Using default."
            )
            max_notifications = self.model.NOTIFICATIONS_MAX_PER_USER_DEFAULT
        return max_notifications

    def user_unread_count(self, user_pk: int) -> int:
        """returns the cached unread count for a user given by user PK

        Will return -1 if user can not be found
        """
        cache_key = self._user_notification_cache_key(user_pk)
        unread_count = cache.get(key=cache_key)
        if not unread_count:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                unread_count = -1
            else:
                logger.debug(
                    'Updating notification cache for user with pk %s', user_pk
                )
                unread_count = user.notification_set.filter(viewed=False).count()
                cache.set(
                    key=cache_key,
                    value=unread_count,
                    timeout=self.USER_NOTIFICATION_COUNT_CACHE_DURATION
                )
        else:
            logger.debug(
                'Returning notification count from cache for user with pk %s', user_pk
            )

        return unread_count

    @classmethod
    def invalidate_user_notification_cache(cls, user_pk: int) -> None:
        cache.delete(key=cls._user_notification_cache_key(user_pk))
        logger.debug('Invalided notification cache for user with pk %s', user_pk)

    @classmethod
    def _user_notification_cache_key(cls, user_pk: int) -> str:
        return f'{cls.USER_NOTIFICATION_COUNT_PREFIX}_{user_pk}'
