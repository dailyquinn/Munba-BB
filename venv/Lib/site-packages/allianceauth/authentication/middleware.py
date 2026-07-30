from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

import logging

logger = logging.getLogger(__name__)


class UserSettingsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        """Django Middleware: User Settings."""

        # Intercept the built in django /setlang/ view and also save it to Database.
        # Note the annoymous user check, only logged in users will ever hit the DB here
        if request.path == '/i18n/setlang/' and not request.user.is_anonymous:
            try:
                request.user.profile.language = request.POST['language']
                request.user.profile.save()
            except Exception as e:
                logger.exception(e)

        # Only act during the login flow, _after_ user is activated (step 2: post-sso)
        elif request.path == '/sso/login' and not request.user.is_anonymous:
            # Set the Language Cookie, if it doesnt match the DB
            # Null = hasnt been set by the user ever, dont act.
            try:
                if request.user.profile.language != request.LANGUAGE_CODE and request.user.profile.language is not None:
                    response.set_cookie(key=settings.LANGUAGE_COOKIE_NAME,
                                        value=request.user.profile.language,
                                        max_age=settings.LANGUAGE_COOKIE_AGE)
            except Exception as e:
                logger.exception(e)

            # AA v3 NIGHT_MODE
            # Set our Night mode flag from the DB
            # Null = hasnt been set by the user ever, dont act.
            #
            # Night mode intercept is not needed in this middleware.
            # is saved direct to DB in NightModeRedirectView
            try:
                if request.user.profile.night_mode is not None:
                    request.session["NIGHT_MODE"] = request.user.profile.night_mode
            except Exception as e:
                logger.exception(e)

            # AA v4 Themes
            # Null = has not been set by the user ever, dont act
            # DEFAULT_THEME or DEFAULT_THEME_DARK will be used in get_theme()
            try:
                if request.user.profile.theme is not None:
                    request.session["THEME"] = request.user.profile.theme
            except Exception as e:
                logger.exception(e)

        # Minimize Menu
        try:
            request.session["MINIMIZE_SIDEBAR"] = request.user.profile.minimize_sidebar
        except Exception as e:
            pass  # We don't care that an anonymous user has no profile (not logged in)

        return response
