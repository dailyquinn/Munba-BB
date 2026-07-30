from django import forms
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from allianceauth.authentication.models import User


class RegistrationForm(forms.Form):
    email = forms.EmailField(label=_('Email'), max_length=254, required=True)

    class _meta:
        model = User


class UserProfileForm(ModelForm):
    """Allows specifying FK querysets through kwarg"""

    def __init__(self, querysets=None, *args, **kwargs):
        querysets = querysets or {}
        super().__init__(*args, **kwargs)
        for field, qs in querysets.items():
            self.fields[field].queryset = qs


class UserChangeForm(BaseUserChangeForm):
    """Add custom cleaning to UserChangeForm"""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")  # Inject current request into form object
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.request.user.is_superuser:
            if self.instance:
                current_restricted = set(
                    self.instance.groups.filter(
                        authgroup__restricted=True
                    ).values_list("pk", flat=True)
                )
            else:
                current_restricted = set()
            new_restricted = set(
                cleaned_data["groups"].filter(
                    authgroup__restricted=True
                ).values_list("pk", flat=True)
            )
            if current_restricted != new_restricted:
                restricted_removed = current_restricted - new_restricted
                restricted_added = new_restricted - current_restricted
                restricted_changed = restricted_removed | restricted_added
                restricted_names_qs = Group.objects.filter(
                    pk__in=restricted_changed
                ).values_list("name", flat=True)
                restricted_names = ",".join(list(restricted_names_qs))
                raise ValidationError(
                    {
                        "groups": _(
                            "You are not allowed to add or remove these "
                            "restricted groups: %s" % restricted_names
                        )
                    }
                )
