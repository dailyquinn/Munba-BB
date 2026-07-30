from django import forms

from .constants import DEFAULT_FOLDER_ICON_CLASSES
from .models import MenuItem


class FolderMenuItemAdminForm(forms.ModelForm):
    """A form for changing folder items."""

    class Meta:
        model = MenuItem
        fields = ["text", "classes", "order", "is_hidden"]

    def clean(self):
        data = super().clean()
        if not data["classes"]:
            data["classes"] = DEFAULT_FOLDER_ICON_CLASSES
        return data


class _BasedMenuItemAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = MenuItem.objects.filter_folders().order_by(
            "text"
        )
        self.fields["parent"].required = False
        self.fields["parent"].widget = forms.Select(
            choices=self.fields["parent"].widget.choices
        )  # disable modify buttons


class AppMenuItemAdminForm(_BasedMenuItemAdminForm):
    """A form for changing app items."""

    class Meta:
        model = MenuItem
        fields = ["order", "parent", "is_hidden"]


class LinkMenuItemAdminForm(_BasedMenuItemAdminForm):
    """A form for changing link items."""

    class Meta:
        model = MenuItem
        fields = ["text", "url", "classes", "order", "parent", "is_hidden"]
        widgets = {
            "url": forms.TextInput(attrs={"size": "100"}),
        }
