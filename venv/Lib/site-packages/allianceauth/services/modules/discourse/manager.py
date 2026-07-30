import logging
import requests
import re
from django.conf import settings
from django.core.cache import cache
from hashlib import md5
from . import providers
logger = logging.getLogger(__name__)

GROUP_CACHE_MAX_AGE = getattr(settings, 'DISCOURSE_GROUP_CACHE_MAX_AGE', 2 * 60 * 60)  # default 2 hours


class DiscourseError(Exception):
    def __init__(self, endpoint, errors):
        self.endpoint = endpoint
        self.errors = errors

    def __str__(self):
        return f"API execution failed.\nErrors: {self.errors}\nEndpoint: {self.endpoint}"


class DiscourseManager:

    def __init__(self):
        pass

    REVOKED_EMAIL = 'revoked@localhost'
    SUSPEND_DAYS = 99999
    SUSPEND_REASON = "Disabled by auth."

    @staticmethod
    def _get_groups():
        data = providers.discourse.client.groups()
        return [g for g in data if not g['automatic']]

    @staticmethod
    def _create_group(name):
        return providers.discourse.client.create_group(name=name[:20], visible=True)['basic_group']

    @staticmethod
    def _generate_cache_group_name_key(name):
        return 'DISCOURSE_GROUP_NAME__%s' % md5(name.encode('utf-8')).hexdigest()

    @staticmethod
    def _generate_cache_group_id_key(g_id):
        return 'DISCOURSE_GROUP_ID__%s' % g_id

    @staticmethod
    def __group_name_to_id(name):
        name = DiscourseManager._sanitize_groupname(name)

        def get_or_create_group():
            groups = DiscourseManager._get_groups()
            for g in groups:
                if g['name'].lower() == name.lower():
                    return g['id']
            return DiscourseManager._create_group(name)['id']

        return cache.get_or_set(DiscourseManager._generate_cache_group_name_key(name), get_or_create_group,
                                GROUP_CACHE_MAX_AGE)

    @staticmethod
    def __group_id_to_name(g_id):
        def get_group_name():
            groups = DiscourseManager._get_groups()
            for g in groups:
                if g['id'] == g_id:
                    return g['name']
            raise KeyError("Group ID %s not found on Discourse" % g_id)

        return cache.get_or_set(DiscourseManager._generate_cache_group_id_key(g_id), get_group_name,
                                GROUP_CACHE_MAX_AGE)

    @staticmethod
    def __add_user_to_group(g_id, username):
        providers.discourse.client.add_group_member(g_id, username)

    @staticmethod
    def __remove_user_from_group(g_id, uid):
        providers.discourse.client.delete_group_member(g_id, uid)

    @staticmethod
    def __generate_group_dict(names):
        group_dict = {}
        for name in names:
            group_dict[name] = DiscourseManager.__group_name_to_id(name)
        return group_dict

    @staticmethod
    def __get_user_groups(username):
        data = DiscourseManager.__get_user(username)
        return [g['id'] for g in data['groups'] if not g['automatic']]

    @staticmethod
    def __user_name_to_id(name, silent=False):
        data = DiscourseManager.__get_user(name)
        return data['user']['id']

    @staticmethod
    def __get_user(username, silent=False):
        return providers.discourse.client.user(username)

    @staticmethod
    def __activate_user(username):
        u_id = DiscourseManager.__user_name_to_id(username)
        providers.discourse.client.activate(u_id)

    @staticmethod
    def __update_user(username, **kwargs):
        u_id = DiscourseManager.__user_name_to_id(username)
        providers.discourse.client.update_user(endpoint, u_id, **kwargs)

    @staticmethod
    def __create_user(username, email, password):
        providers.discourse.client.create_user(username, username, email, password)

    @staticmethod
    def __check_if_user_exists(username):
        try:
            DiscourseManager.__user_name_to_id(username)
            return True
        except DiscourseError:
            return False

    @staticmethod
    def __suspend_user(username):
        u_id = DiscourseManager.__user_name_to_id(username)
        return providers.discourse.client.suspend(u_id, DiscourseManager.SUSPEND_DAYS, DiscourseManager.SUSPEND_REASON)

    @staticmethod
    def __unsuspend(username):
        u_id = DiscourseManager.__user_name_to_id(username)
        return providers.discourse.client.unsuspend(u_id)

    @staticmethod
    def __set_email(username, email):
        return providers.discourse.client.update_email(username, email)

    @staticmethod
    def __logout(u_id):
        return providers.discourse.client.log_out(u_id)

    @staticmethod
    def __get_user_by_external(u_id):
        data = providers.discourse.client.user_by_external_id(u_id)
        return data

    @staticmethod
    def __user_id_by_external_id(u_id):
        data = DiscourseManager.__get_user_by_external(u_id)
        return data['user']['id']

    @staticmethod
    def _sanitize_name(name):
        name = name.replace(' ', '_')
        name = name.replace("'", '')
        name = name.lstrip(' _')
        name = name[:20]
        name = name.rstrip(' _')
        return name

    @staticmethod
    def _sanitize_username(username):
        return DiscourseManager._sanitize_name(username)

    @staticmethod
    def _sanitize_groupname(name):
        name = re.sub(r'[^\w]', '', name)
        name = DiscourseManager._sanitize_name(name)
        if len(name) < 3:
            name = "Group " + name
        return name

    @staticmethod
    def update_groups(user):
        groups = [DiscourseManager._sanitize_groupname(user.profile.state.name)]
        for g in user.groups.all():
            groups.append(DiscourseManager._sanitize_groupname(str(g)))
        logger.debug(f"Updating discourse user {user} groups to {groups}")
        group_dict = DiscourseManager.__generate_group_dict(groups)
        inv_group_dict = {v: k for k, v in group_dict.items()}
        discord_user = DiscourseManager.__get_user_by_external(user.pk)
        username = discord_user['username']
        uid = discord_user['id']
        user_groups = DiscourseManager.__get_user_groups(username)
        add_groups = [group_dict[x] for x in group_dict if not group_dict[x] in user_groups]
        rem_groups = [x for x in user_groups if x not in inv_group_dict]
        if add_groups:
            logger.info(
                f"Updating discourse user {username} groups: adding {add_groups}")
            for g in add_groups:
                DiscourseManager.__add_user_to_group(g, username)
        if rem_groups:
            logger.info(
                f"Updating discourse user {username} groups: removing {rem_groups}")
            for g in rem_groups:
                DiscourseManager.__remove_user_from_group(g, uid)

    @staticmethod
    def disable_user(user):
        logger.debug("Disabling user %s Discourse access." % user)
        d_user = DiscourseManager.__get_user_by_external(user.pk)
        DiscourseManager.__logout(d_user['user']['id'])
        logger.info("Disabled user %s Discourse access." % user)
        return True
