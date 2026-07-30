import logging
from functools import partial

from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.signals import m2m_changed
from django.db.models.signals import pre_delete
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .hooks import ServicesHook
from .tasks import disable_user, update_groups_for_user

from allianceauth.authentication.models import State, UserProfile
from allianceauth.authentication.signals import state_changed
from allianceauth.eveonline.models import EveCharacter

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=User.groups.through)
def m2m_changed_user_groups(sender, instance, action, *args, **kwargs):
    logger.debug(
        "%s: Received m2m_changed from groups with action %s", instance, action
    )
    if instance.pk and (
        action == "post_add" or action == "post_remove" or action == "post_clear"
    ):
        if isinstance(instance, User):
            logger.debug(
                "Waiting for commit to trigger service group update for %s", instance
            )
            transaction.on_commit(partial(update_groups_for_user.delay, instance.pk))
        elif (
            isinstance(instance, Group)
            and kwargs.get("model") is User
            and "pk_set" in kwargs
        ):
            for user_pk in kwargs["pk_set"]:
                logger.debug(
                    "%s: Waiting for commit to trigger service group update for user", user_pk
                )
                transaction.on_commit(partial(update_groups_for_user.delay, user_pk))


@receiver(m2m_changed, sender=User.user_permissions.through)
def m2m_changed_user_permissions(sender, instance, action, *args, **kwargs):
    logger.debug(f"Received m2m_changed from user {instance} permissions with action {action}")
    logger.debug('sender: %s' % sender)
    if instance.pk and (action == "post_remove" or action == "post_clear"):
        logger.debug(f"Permissions changed for user {instance}, re-validating services")
        # Checking permissions for a single user is quite fast, so we don't need to validate
        # That the permissions is a service permission, unlike groups.

        def validate_all_services():
            logger.debug(f"Validating all services for user {instance}")
            for svc in ServicesHook.get_services():
                try:
                    svc.validate_user(instance)
                except:
                    logger.exception(
                        f'Exception running validate_user for services module {svc} on user {instance}')

        transaction.on_commit(lambda: validate_all_services())


@receiver(m2m_changed, sender=Group.permissions.through)
def m2m_changed_group_permissions(sender, instance, action, pk_set, *args, **kwargs):
    logger.debug(f"Received m2m_changed from group {instance} permissions with action {action}")
    if instance.pk and (action == "post_remove" or action == "post_clear"):
        logger.debug(f"Checking if service permission changed for group {instance}")
        # As validating an entire groups service could lead to many thousands of permission checks
        # first we check that one of the permissions changed is, in fact, a service permission.
        perms = Permission.objects.filter(pk__in=pk_set)
        got_change = False
        service_perms = [svc.access_perm for svc in ServicesHook.get_services()]
        for perm in perms:
            natural_key = perm.natural_key()
            path_perm = f"{natural_key[1]}.{natural_key[0]}"
            if path_perm not in service_perms:
                # Not a service permission, keep searching
                continue
            for svc in ServicesHook.get_services():
                if svc.access_perm == path_perm:
                    logger.debug(f"Permissions changed for group {instance} on service {svc}, re-validating services for groups users")

                    def validate_all_groups_users_for_service():
                        logger.debug(f"Performing validation for service {svc}")
                        for user in instance.user_set.all():
                            svc.validate_user(user)

                    transaction.on_commit(validate_all_groups_users_for_service)
                    got_change = True
                    break  # Found service, break out of services iteration and go back to permission iteration
        if not got_change:
            logger.debug(f"Permission change for group {instance} was not service permission, ignoring")


@receiver(m2m_changed, sender=State.permissions.through)
def m2m_changed_state_permissions(sender, instance, action, pk_set, *args, **kwargs):
    logger.debug(f"Received m2m_changed from state {instance} permissions with action {action}")
    if instance.pk and (action == "post_remove" or action == "post_clear"):
        logger.debug(f"Checking if service permission changed for state {instance}")
        # As validating an entire groups service could lead to many thousands of permission checks
        # first we check that one of the permissions changed is, in fact, a service permission.
        perms = Permission.objects.filter(pk__in=pk_set)
        got_change = False
        service_perms = [svc.access_perm for svc in ServicesHook.get_services()]
        for perm in perms:
            natural_key = perm.natural_key()
            path_perm = f"{natural_key[1]}.{natural_key[0]}"
            if path_perm not in service_perms:
                # Not a service permission, keep searching
                continue
            for svc in ServicesHook.get_services():
                if svc.access_perm == path_perm:
                    logger.debug(f"Permissions changed for state {instance} on service {svc}, re-validating services for state users")

                    def validate_all_state_users_for_service():
                        logger.debug(f"Performing validation for service {svc}")
                        for profile in instance.userprofile_set.all():
                            svc.validate_user(profile.user)

                    transaction.on_commit(validate_all_state_users_for_service)
                    got_change = True
                    break  # Found service, break out of services iteration and go back to permission iteration
        if not got_change:
            logger.debug(f"Permission change for state {instance} was not service permission, ignoring")


@receiver(state_changed)
def check_service_accounts_state_changed(sender, user, state, **kwargs):
    logger.debug(f"Received state_changed from {user} to state {state}")
    for svc in ServicesHook.get_services():
        svc.validate_user(user)
        svc.update_groups(user)


@receiver(pre_delete, sender=User)
def pre_delete_user(sender, instance, *args, **kwargs):
    logger.debug("Received pre_delete from %s" % instance)
    disable_user(instance)


@receiver(pre_save, sender=User)
def disable_services_on_inactive(sender, instance, *args, **kwargs):
    logger.debug("Received pre_save from %s" % instance)
    # check if user is being marked active/inactive
    if not instance.pk:
        # new model being created
        return
    try:
        old_instance = User.objects.get(pk=instance.pk)
        if old_instance.is_active and not instance.is_active:
            logger.info("Disabling services for inactivation of user %s" % instance)
            disable_user(instance)
    except User.DoesNotExist:
        pass


@receiver(pre_save, sender=UserProfile)
def process_main_character_change(sender, instance, *args, **kwargs):
    if not instance.pk:
        # ignore new model being created
        return
    try:
        logger.debug(
            "Received pre_save from %s for process_main_character_change", instance
        )
        old_instance = UserProfile.objects.get(pk=instance.pk)
        if old_instance.main_character and not instance.main_character:
            logger.info(
                "Disabling services due to loss of main character for user %s",
                instance.user
            )
            disable_user(instance.user)
        elif old_instance.main_character != instance.main_character:
            logger.info(
                "Updating Names due to change of main character for user %s",
                instance.user
            )
            for svc in ServicesHook.get_services():
                try:
                    svc.validate_user(instance.user)
                    svc.sync_nickname(instance.user)
                except:
                    logger.exception(
                        "Exception running sync_nickname for services module %s "
                        "on user %s",
                        svc,
                        instance
                    )

    except UserProfile.DoesNotExist:
        pass


@receiver(pre_save, sender=EveCharacter)
def process_main_character_update(sender, instance, *args, **kwargs):
    try:
        if instance.userprofile:
            logger.debug(
                "Received pre_save from %s for process_main_character_update",
                instance
            )
            old_instance = EveCharacter.objects.get(pk=instance.pk)
            if not instance.character_name == old_instance.character_name or \
                not instance.corporation_name == old_instance.corporation_name or \
                not instance.alliance_name == old_instance.alliance_name:
                logger.info(f"syncing service nickname for user {instance.userprofile.user}")

                for svc in ServicesHook.get_services():
                    try:
                        svc.validate_user(instance.userprofile.user)
                        svc.sync_nickname(instance.userprofile.user)
                    except:
                        logger.exception(f'Exception running sync_nickname for services module {svc} on user {instance}')

    except ObjectDoesNotExist:  # not a main char ignore
        pass
