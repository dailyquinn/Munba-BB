import logging

from django.contrib.auth.models import Group, User
from django.db.models import Q, QuerySet

from allianceauth.authentication.models import State
from .models import GroupRequest


logger = logging.getLogger(__name__)


class GroupManager:

    @classmethod
    def get_joinable_groups_for_user(
        cls, user: User, include_hidden=True
    ) -> QuerySet[Group]:
        """get groups a user could join incl. groups already joined"""
        groups_qs = cls.get_joinable_groups(user.profile.state)

        if not user.has_perm('groupmanagement.request_groups'):
            groups_qs = groups_qs.filter(authgroup__public=True)

        if not include_hidden:
            groups_qs = groups_qs.filter(authgroup__hidden=False)

        return groups_qs

    @staticmethod
    def get_joinable_groups(state: State) -> QuerySet[Group]:
        """get groups that can be joined by user with given state"""
        return (
            Group.objects
            .exclude(authgroup__internal=True)
            .filter(Q(authgroup__states=state) | Q(authgroup__states=None))
        )

    @staticmethod
    def get_all_non_internal_groups() -> QuerySet[Group]:
        """get groups that are not internal"""
        return Group.objects.exclude(authgroup__internal=True)

    @staticmethod
    def get_group_leaders_groups(user: User) -> QuerySet[Group]:
        return (
            Group.objects.filter(authgroup__group_leaders=user)
            | Group.objects.filter(
                authgroup__group_leader_groups__in=list(user.groups.all())
            )
        )

    @staticmethod
    def joinable_group(group: Group, state: State) -> bool:
        """
        Check if a group is a user/state joinable group, i.e.
        not an internal group for Corp, Alliance, Members etc,
        or restricted from the user's current state.
        :param group: django.contrib.auth.models.Group object
        :param state: allianceauth.authentication.State object
        :return: bool True if its joinable, False otherwise
        """
        if (
            len(group.authgroup.states.all()) != 0
            and state not in group.authgroup.states.all()
        ):
            return False
        return not group.authgroup.internal

    @staticmethod
    def check_internal_group(group: Group) -> bool:
        """
        Check if a group is auditable, i.e not an internal group
        :param group: django.contrib.auth.models.Group object
        :return: bool True if it is auditable, false otherwise
        """
        return not group.authgroup.internal

    @staticmethod
    def has_management_permission(user: User) -> bool:
        return user.has_perm('auth.group_management')

    @classmethod
    def can_manage_groups(cls, user:User) -> bool:
        """
        For use with user_passes_test decorator.
        Check if the user can manage groups. Either has the
        auth.group_management permission or is a leader of at least one group
        and is also a Member.
        :param user: django.contrib.auth.models.User for the request
        :return: bool True if user can manage groups, False otherwise
        """
        if user.is_authenticated:
            return (
                cls.has_management_permission(user)
                or cls.get_group_leaders_groups(user)
            )
        return False

    @classmethod
    def can_manage_group(cls, user: User, group: Group) -> bool:
        """
        Check user has permission to manage the given group
        :param user: User object to test permission of
        :param group: Group object the user is attempting to manage
        :return: True if the user can manage the group
        """
        if user.is_authenticated:
            return (
                cls.has_management_permission(user)
                or cls.get_group_leaders_groups(user).filter(pk=group.pk).exists()
            )
        return False

    @classmethod
    def pending_requests_count_for_user(cls, user: User) -> int:
        """Returns the number of pending group requests for the given user"""
        if cls.has_management_permission(user):
            return GroupRequest.objects.all().count()
        return (
            GroupRequest.objects
            .filter(group__in=list(cls.get_group_leaders_groups(user)))
            .count()
        )
