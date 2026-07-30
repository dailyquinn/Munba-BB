from allianceauth import hooks
from allianceauth.theme.hooks import ThemeHook


CSS_STATICS = [{
    "url": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/css/bootstrap.min.css",
    "integrity": "sha512-jnSuA4Ss2PkkikSOLtYs8BlYIeeIK1h99ty4YfvRPAlzr377vr3CXDb7sb7eEEBYjDtcYj+AjBH3FLv5uSJuXg=="
}]

JS_STATICS = [{
    "url": "https://cdnjs.cloudflare.com/ajax/libs/popper.js/2.11.8/umd/popper.min.js",
    "integrity": "sha512-TPh2Oxlg1zp+kz3nFA0C5vVC6leG/6mm1z9+mA81MI5eaUVqasPLO8Cuk4gMF4gUfP5etR73rgU/8PNMsSesoQ=="
}, {
    "url": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/js/bootstrap.min.js",
    "integrity": "sha512-ykZ1QQr0Jy/4ZkvKuqWn4iF3lqPZyij9iRv6sGqLRdTPkY69YX6+7wvVGmsdBbiIfN/8OdsI7HABjvEok6ZopQ=="
}]


class BootstrapThemeHook(ThemeHook):
    """
    Bootstrap in all its glory!
    https://getbootstrap.com/
    """

    def __init__(self):
        ThemeHook.__init__(
            self,
            "Bootstrap",
            "Powerful, extensible, and feature-packed frontend toolkit.",
            html_tags={"data-theme": "bootstrap"},
            css=CSS_STATICS,
            js=JS_STATICS,
            header_padding="3.5em"
        )


class BootstrapDarkThemeHook(ThemeHook):
    """
    Bootstrap in all its glory!, but _dark_
    https://getbootstrap.com/
    """

    def __init__(self):
        ThemeHook.__init__(
            self,
            "Bootstrap Dark",
            "Powerful, extensible, and feature-packed frontend toolkit.",
            html_tags={"data-theme": "bootstrap-dark", "data-bs-theme":"dark"},
            css=CSS_STATICS,
            js=JS_STATICS,
            header_padding="3.5em"
        )


@hooks.register('theme_hook')
def register_bootstrap_dark_hook():
    return BootstrapDarkThemeHook()


@hooks.register('theme_hook')
def register_bootstrap_hook():
    return BootstrapThemeHook()
