import logging

from celery import shared_task
from django.contrib.auth.models import User
from .hooks import ServicesHook
from celery_once import QueueOnce as BaseTask, AlreadyQueued
from django.core.cache import cache


logger = logging.getLogger(__name__)


class QueueOnce(BaseTask):
    once = BaseTask.once
    once['graceful'] = True


class DjangoBackend:
    def __init__(self, settings):
        pass

    @staticmethod
    def raise_or_lock(key, timeout):
        acquired = cache.add(key=key, value="lock", timeout=timeout)
        if not acquired:
            raise AlreadyQueued(int(cache.ttl(key)))

    @staticmethod
    def clear_lock(key):
        return cache.delete(key)


@shared_task(bind=True)
def validate_services(self, pk):
    user = User.objects.get(pk=pk)
    logger.debug(f'Ensuring user {user} has permissions for active services')
    # Iterate through services hooks and have them check the validity of the user
    for svc in ServicesHook.get_services():
        try:
            svc.validate_user(user)
        except:
            logger.exception(f'Exception running validate_user for services module {svc} on user {user}')


def disable_user(user):
    logger.debug('Disabling all services for user %s' % user)
    for svc in ServicesHook.get_services():
        if svc.service_active_for_user(user):
            svc.delete_user(user)


@shared_task
def update_groups_for_user(user_pk: int) -> None:
    """Update groups for all services registered to a user."""
    user = User.objects.get(pk=user_pk)
    logger.debug("%s: Triggering service group update for user", user)
    for svc in ServicesHook.get_services():
        try:
            svc.validate_user(user)
            svc.update_groups(user)
        except Exception:
            logger.exception(
                'Exception running update_groups for services module %s on user %s',
                svc,
                user
            )
