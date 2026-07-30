import re

from django import forms
from django.utils.translation import gettext_lazy as _


class SrpFleetMainForm(forms.Form):
    fleet_name = forms.CharField(required=True, label=_("Fleet Name"))
    fleet_time = forms.DateTimeField(required=True, label=_("Fleet Time"))
    fleet_doctrine = forms.CharField(required=True, label=_("Fleet Doctrine"))


class SrpFleetUserRequestForm(forms.Form):
    additional_info = forms.CharField(required=False, max_length=25, label=_("Additional Info"))
    killboard_link = forms.CharField(
        label=_("Killboard Link (zkillboard.com or kb.evetools.org)"),
        max_length=255,
        required=True

    )

    def clean_killboard_link(self):
        data = self.cleaned_data['killboard_link']

        # Check if it's a link from one of the accepted kill boards
        if not any(
            re.match(regex, data)
            for regex in [
                r"^http[s]?:\/\/zkillboard\.com\/",
                r"^http[s]?:\/\/kb\.evetools\.org\/",
            ]
        ):
            raise forms.ValidationError(
                _("Invalid Link. Please use zkillboard.com or kb.evetools.org")
            )

        if re.match(r"^http[s]?:\/\/zkillboard\.com\/", data) and not data.endswith("/"):
            data += "/"

        # Check if it's an actual kill mail
        if not any(
            re.match(regex, data)
            for regex in [
                r"^http[s]?:\/\/zkillboard\.com\/kill\/\d+\/",
                r"^http[s]?:\/\/kb\.evetools\.org\/kill\/\d+",
            ]
        ):
            raise forms.ValidationError(
                _("Invalid Link. Please post a direct link to a killmail.")
            )

        return data


class SrpFleetMainUpdateForm(forms.Form):
    fleet_aar_link = forms.CharField(required=True, label=_("After Action Report Link"))
