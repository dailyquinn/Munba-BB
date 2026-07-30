from celery import shared_task

from django.contrib.auth.models import Group


@shared_task
def remove_users_not_matching_states_from_group(group_pk: int) -> None:
    """Remove users not matching defined states from related group."""
    group = Group.objects.get(pk=group_pk)
    group.authgroup.remove_users_not_matching_states()
