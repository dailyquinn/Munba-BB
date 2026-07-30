from django.utils.translation import gettext_lazy as _

# Overide ESI messages in the dashboard widget
# when the returned messages are not helpful or out of date
ESI_ERROR_MESSAGE_OVERRIDES = {
    420: _("This software has exceeded the error limit for ESI. "
            "If you are a user, please contact the maintainer of this software."
            " If you are a developer/maintainer, please make a greater "
            "effort in the future to receive valid responses. For tips on how, "
            "come have a chat with us in ##3rd-party-dev-and-esi on the EVE "
            "Online Discord. https://www.eveonline.com/discord")
}
