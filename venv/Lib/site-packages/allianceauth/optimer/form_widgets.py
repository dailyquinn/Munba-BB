"""
Form Widgets
"""

from django import forms
from django.utils.safestring import mark_safe


class DataListWidget(forms.TextInput):
    """
    DataListWidget

    Draws an HTML5 datalist form field
    """

    def __init__(self, data_list, name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._name = name
        self._list = data_list
        self.attrs.update({"list": "list__%s" % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        """
        Render the DataList
        :param name:
        :type name:
        :param value:
        :type value:
        :param attrs:
        :type attrs:
        :param renderer:
        :type renderer:
        :return:
        :rtype:
        """

        text_html = super().render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name

        for item in self._list:
            data_list += '<option value="%s">' % item

        data_list += "</datalist>"

        return mark_safe(text_html + data_list)
