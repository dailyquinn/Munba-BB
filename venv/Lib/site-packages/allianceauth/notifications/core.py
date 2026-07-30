class NotifyApiWrapper:
    """Wrapper to create notify API."""

    def __call__(self, *args, **kwargs):  # provide old API for backwards compatibility
        return self._add_notification(*args, **kwargs)

    def danger(self, user: object, title: str, message: str = None) -> None:
        """Add danger notification for user."""
        self._add_notification(user, title, message, level="danger")

    def info(self, user: object, title: str, message: str = None) -> None:
        """Add info notification for user."""
        self._add_notification(user=user, title=title, message=message, level="info")

    def success(self, user: object, title: str, message: str = None) -> None:
        """Add success notification for user."""
        self._add_notification(user, title, message, level="success")

    def warning(self, user: object, title: str, message: str = None) -> None:
        """Add warning notification for user."""
        self._add_notification(user, title, message, level="warning")

    def _add_notification(
        self, user: object, title: str, message: str = None, level: str = "info"
    ) -> None:
        from .models import Notification

        Notification.objects.notify_user(
            user=user, title=title, message=message, level=level
        )


notify = NotifyApiWrapper()
