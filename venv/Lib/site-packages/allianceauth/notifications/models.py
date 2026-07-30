import logging
from typing import ClassVar

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .managers import NotificationManager

logger = logging.getLogger(__name__)


class Notification(models.Model):
    """Notification to a user within Auth"""

    NOTIFICATIONS_MAX_PER_USER_DEFAULT = 50
    NOTIFICATIONS_REFRESH_TIME_DEFAULT = 30

    class Level(models.TextChoices):
        """A notification level."""

        DANGER = 'danger', _('danger')  #:
        WARNING = 'warning', _('warning')  #:
        INFO = 'info', _('info')  #:
        SUCCESS = 'success', _('success')  #:

        @classmethod
        def from_old_name(cls, name: str) -> object:
            """Map old name to enum.

            Raises ValueError for invalid names.
            """
            name_map = {
                "CRITICAL": cls.DANGER,
                "ERROR": cls.DANGER,
                "WARN": cls.WARNING,
                "INFO": cls.INFO,
                "DEBUG": cls.SUCCESS,
            }
            try:
                return name_map[name]
            except KeyError:
                raise ValueError(f"Unknown name: {name}") from None

    # LEVEL_CHOICES = (
    #     ('danger', 'CRITICAL'),
    #     ('danger', 'ERROR'),
    #     ('warning', 'WARN'),
    #     ('info', 'INFO'),
    #     ('success', 'DEBUG'),
    # )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.CharField(choices=Level.choices, max_length=10, default=Level.INFO)
    title = models.CharField(max_length=254)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    viewed = models.BooleanField(default=False, db_index=True)

    objects: ClassVar[NotificationManager] = NotificationManager()

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"

    def save(self, *args, **kwargs):
        # overriden save to ensure cache is invaidated on very call
        super().save(*args, **kwargs)
        Notification.objects.invalidate_user_notification_cache(self.user.pk)

    def delete(self, *args, **kwargs):
        # overriden delete to ensure cache is invaidated on very call
        super().delete(*args, **kwargs)
        Notification.objects.invalidate_user_notification_cache(self.user.pk)

    def mark_viewed(self) -> None:
        """Mark notification as viewed."""
        logger.info("Marking notification as viewed: %s" % self)
        self.viewed = True
        self.save()

    def set_level(self, level_name: str) -> None:
        """Set notification level according to old level name, e.g. 'CRITICAL'.

        Raises ValueError on invalid level names.
        """
        self.level = self.Level.from_old_name(level_name)
        self.save()
