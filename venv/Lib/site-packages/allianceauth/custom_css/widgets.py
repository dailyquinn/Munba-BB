"""
Form widgets for custom_css app
"""

# Django
from django import forms

# Alliance Auth
from allianceauth.custom_css.models import CustomCSS


class CssEditorWidget(forms.Textarea):
    """
    Widget for editing CSS
    """

    def __init__(self, attrs=None):
        default_attrs = {"class": "custom-css-editor"}

        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)

    # For when we want to add some sort of syntax highlight to it, which is not that
    # easy to do on a textarea field though.
    # `highlight.js` is just used as an example here, and doesn't work on a textarea field.
    # class Media:
    #     css = {
    #         "all": (
    #             "/static/custom_css/libs/highlight.js/11.10.0/styles/github.min.css",
    #         )
    #     }
    #     js = (
    #         "/static/custom_css/libs/highlight.js/11.10.0/highlight.min.js",
    #         "/static/custom_css/libs/highlight.js/11.10.0/languages/css.min.js",
    #         "/static/custom_css/javascript/custom-css.min.js",
    #     )
