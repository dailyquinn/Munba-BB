import functools

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .models import ReservedGroupName


class GroupAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by(Lower('username')),
        required=False,
        widget=FilteredSelectMultiple(verbose_name=_("Users"), is_stacked=False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["users"].initial = self.instance.user_set.all()

    def save(self, commit=True):
        group: Group = super().save(commit=False)

        if commit:
            group.save()

        users = self.cleaned_data["users"]
        if group.pk:
            self._save_m2m_and_users(group, users)
        else:
            self.save_m2m = functools.partial(
                self._save_m2m_and_users, group=group, users=users
            )

        return group

    def _save_m2m_and_users(self, group, users):
        """Save m2m relations incl. users."""
        group.user_set.set(users)
        self._save_m2m()

    def clean_name(self):
        my_name = self.cleaned_data['name']
        if ReservedGroupName.objects.filter(name__iexact=my_name).exists():
            raise ValidationError(
                _("This name has been reserved and can not be used for groups."),
                code='reserved_name'
            )
        return my_name


class ReservedGroupNameAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['created_by'].initial = self.current_user.username
        self.fields['created_at'].initial = _("(auto)")

    created_by = forms.CharField(disabled=True)
    created_at = forms.CharField(disabled=True)

    def clean_name(self):
        my_name = self.cleaned_data['name'].lower()
        if Group.objects.filter(name__iexact=my_name).exists():
            raise ValidationError(
                _("There already exists a group with that name."), code='already_exists'
            )
        return my_name

    def clean_created_at(self):
        return now()
