from allianceauth import hooks
from allianceauth.theme.hooks import ThemeHook


class MateriaThemeHook(ThemeHook):
    """
    Bootswatch Materia Theme
    https://bootswatch.com/materia/
    """

    def __init__(self):
        ThemeHook.__init__(
            self,
            "Materia",
            "Material is the metaphor",
            html_tags={"data-theme": "materia"},
            css=[{
                "url": "https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.3.3/materia/bootstrap.min.css",
                "integrity": "sha512-2S9Do+uTmZmmJpdmAcOKdUrK/YslcvAuRfIF2ws8+BW9AvZXMRZM+o8Wq+PZrfISD6ZlIaeCWWZAdeprXIoYuQ=="
            }],
            js=[{
                "url": "https://cdnjs.cloudflare.com/ajax/libs/popper.js/2.11.8/umd/popper.min.js",
                "integrity": "sha512-TPh2Oxlg1zp+kz3nFA0C5vVC6leG/6mm1z9+mA81MI5eaUVqasPLO8Cuk4gMF4gUfP5etR73rgU/8PNMsSesoQ=="
            }, {
                "url": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/js/bootstrap.min.js",
                "integrity": "sha512-ykZ1QQr0Jy/4ZkvKuqWn4iF3lqPZyij9iRv6sGqLRdTPkY69YX6+7wvVGmsdBbiIfN/8OdsI7HABjvEok6ZopQ=="
            }],
            header_padding="5.25em"
        )


@hooks.register('theme_hook')
def register_materia_hook():
    return MateriaThemeHook()
