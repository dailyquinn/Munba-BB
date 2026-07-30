# flake8: noqa

"""Concurrency testing Discord service tasks

This script will run many Discord service tasks in parallel to test concurrency
Note that it will run against your main Auth database and not test!

Check allianceauth.log for the results.

To run this test start a bunch of celery workers and then run this script directly.
Make sure to also set the environment variable AUTH_PROJECT_PATH to your Auth path
and DJANGO_SETTINGS_MODULE to the relative location of your settings:

Example:
export AUTH_PROJECT_PATH="/home/erik997/dev/python/aa/allianceauth-dev/myauth"
export DJANGO_SETTINGS_MODULE="myauth.settings.local"

Careful: This script will utilize all existing Discord users and make changes!
"""
# start django project
import os
import sys
if not 'AUTH_PROJECT_PATH' in os.environ:
    print('AUTH_PROJECT_PATH is not set')
    exit(1)
if not 'DJANGO_SETTINGS_MODULE' in os.environ:
    print('DJANGO_SETTINGS_MODULE is not set')
    exit(1)
sys.path.insert(0, os.environ['AUTH_PROJECT_PATH'])
import django
django.setup()

# normal imports
import logging
from uuid import uuid1
import random

from django.contrib.auth.models import User, Group

from allianceauth.services.modules.discord.models import DiscordUser
from allianceauth.utils.cache import get_redis_client

logger = logging.getLogger('allianceauth')
MAX_RUNS = 3


def clear_cache():
    redis = get_redis_client()
    redis.flushall()
    logger.info('Cache flushed')

def run_many_updates(runs):
    logger.info('Starting piloting_tasks for %d runs', runs)
    users = list()
    all_groups = Group.objects.all()
    for i in range(runs):
        if not users:
            users = list(User.objects.filter(discord__isnull=False))
        user = users.pop()
        logger.info('%d/%d: Starting run with user %s', i + 1, runs, user)
        # force change of nick
        new_nick = f'Testnick {uuid1().hex}'[:32]
        logger.info(
            '%d/%d: Changing nickname of %s to "%s"', i + 1, runs, user, new_nick
        )
        user.profile.main_character.character_name = new_nick
        user.profile.main_character.save()

        # force change of groups
        user_groups = user.groups.all()
        user.groups.remove(random.choice(user_groups))
        while True:
            new_group = random.choice(all_groups)
            if new_group not in user_groups:
                break
        logger.info('%d/%d: Adding group "%s" to user %s', i + 1, runs, new_group, user)
        user.groups.add(new_group)

    logger.info('All %d runs have been started', runs)

if __name__ == "__main__":
    clear_cache()
    run_many_updates(MAX_RUNS)
