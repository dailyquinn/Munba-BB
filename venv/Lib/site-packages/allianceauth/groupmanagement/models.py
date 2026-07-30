from typing import Set

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from allianceauth.authentication.models import State
from allianceauth.notifications import notify


class GroupRequest(models.Model):
    """Request from a user for joining or leaving a group."""

    leave_request = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username + ":" + self.group.name

    @property
    def main_char(self):
        """
        Legacy property for main character
        :return: self.users main character
        """
        return self.user.profile.main_character

    def notify_leaders(self) -> None:
        """Send notification to all group leaders about this request.

        Note: No translations, because language for each leader is unknown
        """
        if not getattr(settings, 'GROUPMANAGEMENT_REQUESTS_NOTIFICATION', False):
            return
        keyword = "leave" if self.leave_request else "join"
        title = f"Group Management: {keyword.title()} request for {self.group.name}"
        message = f"{self.user} want's to {keyword} {self.group.name}."
        for appover in self.group.authgroup.group_request_approvers():
            notify(user=appover, title=title, message=message, level="info")


class RequestLog(models.Model):
    """Log entry about who joined and left a group and who approved it."""

    request_type = models.BooleanField(null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    request_info = models.CharField(max_length=254)
    action = models.BooleanField(default=False)
    request_actor = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def requestor(self):
        return self.request_info.split(":")[0]

    def type_to_str(self):
        if self.request_type is None:
            return "Removed"
        elif self.request_type is True:
            return "Leave"
        elif self.request_type is False:
            return "Join"

    def action_to_str(self):
        if self.action is True:
            return "Accept"
        elif self.action is False:
            return "Reject"

    def req_char(self):
        usr = self.requestor()
        user = User.objects.get(username=usr)
        return user.profile.main_character


class AuthGroup(models.Model):
    """
    Extends Django Group model with a one-to-one field
    Attributes are accessible via group as if they were in the model
    e.g. group.authgroup.internal

    Logic:
    Internal - not requestable by users, at all. Covers Corp_, Alliance_,
    Members etc groups. Groups are internal by default

    Public - Other options are respected, but any user will be able to become
    and remain a member, even if they have no API etc entered.
    Auth will not manage these groups automatically so user removal is up to
    group managers/leaders.

    Not Internal and:
        Hidden - users cannot view, can request if they have the direct link.
        Not Hidden - Users can view and request the group
        Open - Users are automatically accepted into the group
        Not Open - Users requests must be approved before they are added to the group
    """

    group = models.OneToOneField(Group, on_delete=models.CASCADE, primary_key=True)
    internal = models.BooleanField(
        default=True,
        help_text=_(
            "Internal group, users cannot see, join or request to join this group.<br>"
            "Used for groups such as Members, Corp_*, Alliance_* etc.<br>"
            "<b>Overrides Hidden and Open options when selected.</b>"
        )
    )
    hidden = models.BooleanField(
        default=True,
        help_text=_(
            "Group is hidden from users but can still join with the correct link."
        )
    )
    open = models.BooleanField(
        default=False,
        help_text=_(
            "Group is open and users will be automatically added upon request.<br>"
            "If the group is not open users will need their request manually approved."
        )
    )
    public = models.BooleanField(
        default=False,
        help_text=_(
            "Group is public. Any registered user is able to join this group, with "
            "visibility based on the other options set for this group.<br>"
            "Auth will not remove users from this group automatically when they "
            "are no longer authenticated."
        )
    )
    restricted = models.BooleanField(
        default=False,
        help_text=_(
            "Group is restricted. This means that adding or removing users "
            "for this group requires a superuser admin."
        )
    )
    group_leaders = models.ManyToManyField(
        User,
        related_name='leads_groups',
        blank=True,
        help_text=_(
            "Group leaders can process requests for this group. "
            "Use the <code>auth.group_management</code> permission to allow "
            "a user to manage all groups.<br>"
        )
    )
    group_leader_groups = models.ManyToManyField(
        Group,
        related_name='leads_group_groups',
        blank=True,
        help_text=_(
            "Members of leader groups can process requests for this group. "
            "Use the <code>auth.group_management</code> permission "
            "to allow a user to manage all groups.<br>")
    )
    states = models.ManyToManyField(
        State,
        related_name='valid_states',
        blank=True,
        help_text=_(
            "States listed here will have the ability to join this group provided "
            "they have the proper permissions.<br>"
        )
    )
    description = models.TextField(
        max_length=512,
        blank=True,
        help_text=_(
            "Short description <i>(max. 512 characters)</i> "
            "of the group shown to users."
        )
    )

    class Meta:
        permissions = (
            ("request_groups", _("Can request non-public groups")),
        )
        default_permissions = tuple()

    def __str__(self):
        return self.group.name

    def group_request_approvers(self) -> Set[User]:
        """Return all users who can approve a group request."""
        return set(
            self.group_leaders.all()
            | User.objects.filter(groups__in=list(self.group_leader_groups.all()))
        )

    def remove_users_not_matching_states(self):
        """Remove users not matching defined states from related group."""
        states_qs = self.states.all()
        if states_qs.exists():
            states = list(states_qs)
            non_compliant_users = self.group.user_set.exclude(profile__state__in=states)
            for user in non_compliant_users:
                self.group.user_set.remove(user)


class ReservedGroupName(models.Model):
    """Name that can not be used for groups.

    This enables AA to ignore groups on other services (e.g. Discord) with that name.
    """

    name = models.CharField(
        _('name'),
        max_length=150,
        unique=True,
        help_text=_("Name that can not be used for groups.")
    )
    reason = models.TextField(
        _('reason'), help_text=_("Reason why this name is reserved.")
    )
    created_by = models.CharField(
        _('created by'),
        max_length=255,
        help_text="Name of the user who created this entry."
    )
    created_at = models.DateTimeField(
        _('created at'), default=now, help_text=_("Date when this entry was created")
    )

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if Group.objects.filter(name__iexact=self.name).exists():
            raise RuntimeError(
                f"Save failed. There already exists a group with the name: {self.name}."
            )
        super().save(*args, **kwargs)
