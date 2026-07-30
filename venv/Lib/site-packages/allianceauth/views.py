import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import View

logger = logging.getLogger(__name__)


class NightModeRedirectView(View):
    SESSION_VAR = "NIGHT_MODE"

    def get(self, request, *args, **kwargs):
        request.session[self.SESSION_VAR] = not self.night_mode_state(request)
        if not request.user.is_anonymous:
            try:
                request.user.profile.night_mode = request.session[self.SESSION_VAR]
                request.user.profile.save()
            except Exception as e:
                logger.exception(e)

        return HttpResponseRedirect(request.GET.get("next", "/"))

    @classmethod
    def night_mode_state(cls, request):
        try:
            return request.session.get(cls.SESSION_VAR, False)
        except AttributeError:
            # Session is middleware
            # Sometimes request wont have a session attribute
            return False


class ThemeRedirectView(View):
    THEME_VAR = "THEME"

    def post(self, request, *args, **kwargs):
        theme = request.POST.get('theme', settings.DEFAULT_THEME)
        if not request.user.is_anonymous:
            try:
                request.user.profile.theme = theme
                request.user.profile.save()
                request.session[self.THEME_VAR] = theme
            except Exception as e:
                logger.exception(e)

        return HttpResponseRedirect(request.GET.get("next", "/"))

class MinimizeSidebarRedirectView(View):
    SESSION_VAR = "MINIMIZE_SIDEBAR"

    def post(self, request, *args, **kwargs):
        request.session[self.SESSION_VAR] = not self.minimize_sidebar_state(request)
        if not request.user.is_anonymous:
            try:
                request.user.profile.minimize_sidebar = request.session[self.SESSION_VAR]
                request.user.profile.save()
            except Exception as e:
                logger.exception(e)

        return HttpResponseRedirect(request.GET.get("next", "/"))

    @classmethod
    def minimize_sidebar_state(cls, request):
        try:
            return request.session.get(cls.SESSION_VAR, False)
        except AttributeError:
            # Session is middleware
            # Sometimes request wont have a session attribute
            return False


# TODO: error views should be renamed to a proper function name when possible

def Generic400Redirect(request, *args, **kwargs):
    title = _("Bad Request")
    message = _(
        "Auth encountered an error processing your request, please try again. "
        "If the error persists, please contact the administrators."
    )
    response = _build_error_response(request, title, message, 400)
    return response


def Generic403Redirect(request, *args, **kwargs):
    title = _("Permission Denied")
    message = _(
        "You do not have permission to access the requested page. "
        "If you believe this is in error please contact the administrators."
    )
    response = _build_error_response(request, title, message, 403)
    return response


def Generic404Redirect(request, *args, **kwargs):
    title = _("Page Not Found")
    message = _(
        "Page does not exist. "
        "If you believe this is in error please contact the administrators. "
    )
    response = _build_error_response(request, title, message, 404)
    return response


def Generic500Redirect(request, *args, **kwargs):
    title = _("Internal Server Error")
    message = _(
        "Auth encountered an error processing your request, please try again. "
        "If the error persists, please contact the administrators."
    )
    response = _build_error_response(request, title, message, 500)
    return response


def _build_error_response(request, title, message, status_code) -> HttpResponse:
    context = {"error_title": title, "error_message": message}
    response = render(request, "allianceauth/error.html", context)
    response.status_code = status_code
    return response
