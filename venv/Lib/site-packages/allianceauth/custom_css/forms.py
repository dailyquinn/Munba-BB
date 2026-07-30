"""
Forms for custom_css app
"""

# Alliance Auth Custom CSS
from allianceauth.custom_css.models import CustomCSS
from allianceauth.custom_css.widgets import CssEditorWidget

# Django
from django import forms


class CustomCSSAdminForm(forms.ModelForm):
    """
    Form for editing custom CSS
    """

    class Meta:
        model = CustomCSS
        fields = ("css",)
        widgets = {
            "css": CssEditorWidget(
                attrs={
                    "style": "width: 90%; height: 100%;",
                    "data-editor": "code-highlight",
                    "data-language": "css",
                }
            )
        }
