from typing import List, Optional, Union


class ThemeHook:
    """
    Theme hook for injecting a Bootstrap 5 Theme and associated JS into alliance auth.
    These can be local or CDN delivered.
    """

    def __init__(self,
        name: str,
        description: str,
        css: List[dict],
        js: List[dict],
        css_template: Optional[str] = None,
        js_template: Optional[str] = None,
        js_type: Optional[str] = None,
        html_tags: Optional[Union[dict, str]] = None,
        header_padding: Optional[str] = "4em"
    ):
        """
        :param name: Theme python name
        :type name: str
        :param description: Theme verbose name
        :type description: str
        :param css: CSS paths to load
        :type css: List[dict]
        :param js: JS paths to load
        :type js: List[dict]
        :param css_template: _description_, defaults to None
        :type css_template: Optional[str], optional
        :param js_template: _description_, defaults to None
        :type js_template: Optional[str], optional
        :param js_type: The type of the JS (e.g.: 'module'), defaults to None
        :type js_type: Optional[str], optional
        :param html_tags: Attributes added to the `<html>` tag, defaults to None
        :type html_tags: Optional[dict|str], optional
        :param header_padding: Top padding, defaults to "4em"
        :type header_padding: Optional[str], optional
        """

        self.name = name
        self.description = description

        # Direct from CDN
        self.css = css
        self.js = js

        # Load a django template with static file definitions
        self.css_template = css_template
        self.js_template = js_template

        # Define the JS type (e.g.: 'module')
        self.js_type = js_type

        self.html_tags = (
            " ".join([f"{key}={value}" for key, value in html_tags.items()])
            if isinstance(html_tags, dict)
            else html_tags
        )
        self.header_padding = header_padding

    def get_name(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}"
