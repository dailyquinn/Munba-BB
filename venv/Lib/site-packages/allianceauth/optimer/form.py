from django import forms
from django.utils.translation import gettext_lazy as _

from allianceauth.optimer.form_widgets import DataListWidget


class OpForm(forms.Form):
    """
    Create/Edit Fleet Operation Form
    """

    doctrine = forms.CharField(max_length=254, required=True, label=_('Doctrine'))
    system = forms.CharField(max_length=254, required=True, label=_("System"))
    start = forms.DateTimeField(required=True, label=_("Start Time"))
    operation_name = forms.CharField(max_length=254, required=True, label=_("Operation Name"))
    type = forms.CharField(required=False, label=_("Operation Type"))
    fc = forms.CharField(max_length=254, required=True, label=_("Fleet Commander"))
    duration = forms.CharField(max_length=25, required=True, label=_("Duration"))
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "cols": 20, "input_type": "textarea"}),
        required=False,
        label=_("Additional Info"),
        help_text=_("(Optional) Describe the operation with a couple of short words."),
    )

    def __init__(self, *args, **kwargs):
        _data_list = kwargs.pop('data_list', None)

        super().__init__(*args, **kwargs)

        # Add the DataListWidget to our type field
        self.fields['type'].widget = DataListWidget(
            data_list=_data_list, name='data-list'
        )
