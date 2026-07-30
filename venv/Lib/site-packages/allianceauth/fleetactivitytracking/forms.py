from django import forms
from django.utils.translation import gettext_lazy as _


class FatlinkForm(forms.Form):
    fleet = forms.CharField(label=_("Fleet Name"), max_length=50)
    duration = forms.IntegerField(label=_("Duration of fat-link"), required=True, initial=30, min_value=1, max_value=2147483647, help_text=_('Duration of the fat-link in minutes'))
