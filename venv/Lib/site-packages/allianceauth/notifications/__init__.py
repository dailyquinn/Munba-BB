"""
Example
=======

.. code-block:: python

    from allianceauth.notifications.models import Notification


    def notify_user_view(request):
        '''Simple view sending a notification to the user'''

        Notification.objects.notify_user(
                user=request.user,
                title="Some title",
                message="Some message",
                level=Notification.Level.INFO,
            )

"""
from .core import notify  # noqa: F401
