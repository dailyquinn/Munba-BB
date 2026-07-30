from string import Formatter
from django.urls import include, re_path
from typing import Iterable, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.urls import include, re_path
from django.utils.functional import cached_property

from allianceauth.hooks import get_hooks
from allianceauth.menu.hooks import MenuItemHook
from django.conf import settings
from django.urls import include, re_path
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import cached_property

from .models import NameFormatConfig


def get_extension_logger(name):
    """
    Takes the name of a plugin/extension and generates a child logger of the extensions logger
    to be used by the extension to log events to the extensions logger.

    The logging level is determined by the level defined for the parent logger.

    :param: name: the name of the extension doing the logging
    :return: an extensions child logger
    """
    if not isinstance(name, str):
        raise TypeError(f"get_extension_logger takes an argument of type string."
                        f"Instead received argument of type {type(name).__name__}.")

    import logging

    parent_logger = logging.getLogger('extensions')

    logger = logging.getLogger('extensions.' + name)
    logger.name = name
    logger.level = parent_logger.level

    return logger


class ServicesHook:
    """
    Abstract base class for creating a compatible services
    hook. Decorate with @register('services_hook') to have the
    services module registered for callbacks. Must be in
    auth_hook(.py) sub module
    """
    def __init__(self):
        self.name = 'Undefined'
        self.urlpatterns = []
        self.service_ctrl_template = 'services/services_ctrl.html'
        self.access_perm = None

    @property
    def title(self):
        """
        A nicely formatted title of the service, for client facing
        display.
        :return: str
        """
        return self.name.title()

    def delete_user(self, user, notify_user=False):
        """
        Delete the users service account, optionally notify them
        that the service has been disabled
        :param user: Django.contrib.auth.models.User
        :param notify_user: Whether the service should sent a
        notification to the user about the disabling of their
        service account.
        :return: True if the service account has been disabled,
        or False if it doesnt exist.
        """
        pass

    def validate_user(self, user):
        pass

    def sync_nickname(self, user):
        """
        Sync the users nickname
        :param user: Django.contrib.auth.models.User
        :return: None
        """
        pass

    def update_groups(self, user):
        """
        Update the users group membership
        :param user: Django.contrib.auth.models.User
        :return: None
        """
        pass

    def update_all_groups(self):
        """
        Iterate through and update all users groups
        :return: None
        """
        pass

    def service_active_for_user(self, user):
        pass

    def show_service_ctrl(self, user):
        """
        Whether the service control should be displayed to the given user
        who has the given service state. Usually this function wont
        require overloading.
        :param user: django.contrib.auth.models.User
        :return: bool True if the service should be shown
        """
        return self.service_active_for_user(user) or user.is_superuser

    def render_services_ctrl(self, request):
        """
        Render the services control template row
        :param request:
        :return:
        """
        return ''

    def __str__(self):
        return self.name or 'Unknown Service Module'

    class Urls:
        def __init__(self):
            self.auth_activate = ''
            self.auth_set_password = ''
            self.auth_reset_password = ''
            self.auth_deactivate = ''

    @staticmethod
    def get_services():
        for fn in get_hooks('services_hook'):
            yield fn()


class MenuItemHook(MenuItemHook):
    """
    MenuItemHook shim to allianceauth.menu.hooks

    :param MenuItemHook: _description_
    :type MenuItemHook: _type_
    """
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()


class UrlHook:
    """A hook for registering the URLs of a Django app.

    Args:
        - urls: The urls module to include
        - namespace: The URL namespace to apply. This is usually just the app name.
        - base_url: The URL prefix to match against in regex form.
            Example ``r'^app_name/'``.
            This prefix will be applied in front of all URL patterns included.
            It is possible to use the same prefix as existing apps (or no prefix at all),
            but standard URL resolution ordering applies
            (hook URLs are the last ones registered).
        - excluded_views: Optional list of views to be excluded
            from auto-decorating them with the
            default ``main_character_required`` decorator, e.g. to make them public.
            Views must be specified by their qualified name,
            e.g. ``["example.views.my_public_view"]``
    """
    def __init__(
            self,
            urls,
            namespace: str,
            base_url: str,
            excluded_views : Optional[Iterable[str]] = None
    ):
        self.include_pattern = re_path(base_url, include(urls, namespace=namespace))
        self.excluded_views = set(excluded_views or [])


class NameFormatter:
    DEFAULT_FORMAT = getattr(settings, "DEFAULT_SERVICE_NAME_FORMAT", '[{corp_ticker}] {character_name}')

    def __init__(self, service, user):
        """
        :param service: ServicesHook of the service to generate the name for.
        :param user: django.contrib.auth.models.User to format name for
        """
        self.service = service
        self.user = user

    def format_name(self):
        """
        :return: str Generated name
        """
        format_data = self.get_format_data()
        return Formatter().vformat(self.string_formatter, args=[], kwargs=format_data).strip()

    def get_format_data(self):
        try:
            character_name = self.user.profile.main_character.character_name
            character_id = self.user.profile.main_character.character_id

            corp_name = self.user.profile.main_character.corporation_name
            corp_id = self.user.profile.main_character.corporation_id
            corp_ticker = self.user.profile.main_character.corporation_ticker

            alliance_name = self.user.profile.main_character.alliance_name
            alliance_id = self.user.profile.main_character.alliance_id
            alliance_ticker = self.user.profile.main_character.alliance_ticker
        except (AttributeError, ObjectDoesNotExist):
            character_name = self.user.username if self._default_to_username else ""
            character_id = ""

            corp_name = ""
            corp_id = ""
            corp_ticker = ""

            alliance_name = ""
            alliance_id = ""
            alliance_ticker = ""

        format_data = {
            'character_name': character_name,
            'character_id': character_id if character_id else "",
            'corp_ticker': corp_ticker if corp_ticker else "",
            'corp_name': corp_name if corp_name else "",
            'corp_id': corp_id if corp_id else "",
            'alliance_name': alliance_name if alliance_name else "",
            'alliance_id': alliance_id if alliance_id else "",
            'alliance_ticker': alliance_ticker if alliance_ticker else "",
            'username': self.user.username,
        }

        format_data['alliance_or_corp_name'] = format_data['alliance_name'] or format_data['corp_name']
        format_data['alliance_or_corp_ticker'] = format_data['alliance_ticker'] or format_data['corp_ticker']

        return format_data

    @cached_property
    def formatter_config(self):
        format_config = NameFormatConfig.objects.filter(service_name=self.service.name,
                                                        states__pk=self.user.profile.state.pk)

        if format_config.exists():
            return format_config[0]
        return None

    @cached_property
    def string_formatter(self):
        """
        Try to get the config format first
        Then the service default
        Before finally defaulting to global default
        :return: str
        """
        return getattr(self.formatter_config, 'format', self.default_formatter)

    @cached_property
    def default_formatter(self):
        return getattr(self.service, 'name_format', self.DEFAULT_FORMAT)

    @cached_property
    def _default_to_username(self):
        """
        Default to a users username if they have no main character.
        Default is True
        :return: bool
        """
        return getattr(self.formatter_config, 'default_to_username', True)
