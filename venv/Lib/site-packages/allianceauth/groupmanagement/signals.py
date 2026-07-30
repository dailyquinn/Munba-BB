import logging
from django.contrib.auth.models import Group
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from allianceauth.authentication.signals import state_changed

from .models import AuthGroup, ReservedGroupName

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Group)
def find_new_name_for_conflicting_groups(sender, instance, **kwargs):
    """Find new name for a group which name is already reserved."""
    new_name = instance.name
    num = 0
    while ReservedGroupName.objects.filter(name__iexact=new_name).exists():
        num += 1
        new_name = f"{instance.name}_{num}"
    instance.name = new_name


@receiver(post_save, sender=Group)
def create_auth_group(sender, instance, created, **kwargs):
    """Create the AuthGroup model when a group is created."""
    if created:
        AuthGroup.objects.create(group=instance)


@receiver(state_changed)
def check_groups_on_state_change(sender, user, state, **kwargs):
    logger.debug(
        f"Checking group memberships for {user} based on new state {state}"
    )
    state_groups = (
        user.groups.select_related("authgroup").exclude(authgroup__states=None)
    )
    for group in state_groups:
        if not group.authgroup.states.filter(id=state.id).exists():
            logger.info(
                f"Removing user {user} from group {group} due to missing state"
            )
            user.groups.remove(group)
