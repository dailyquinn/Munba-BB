import logging

import requests
from django_registration.backends.activation.views import (
    REGISTRATION_SALT, ActivationView as BaseActivationView,
    RegistrationView as BaseRegistrationView,
)
from django_registration.signals import user_registered

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from esi.decorators import token_required
from esi.models import Token

from allianceauth.eveonline.models import EveCharacter
from allianceauth.hooks import get_hooks

from .constants import ESI_ERROR_MESSAGE_OVERRIDES
from .core.celery_workers import active_tasks_count, queued_tasks_count
from allianceauth.templatetags.admin_status import _celery_stats
from .forms import RegistrationForm
from .models import CharacterOwnership

if 'allianceauth.eveonline.autogroups' in settings.INSTALLED_APPS:
    _has_auto_groups = True
    from allianceauth.eveonline.autogroups.models import *  # noqa: F401, F403
else:
    _has_auto_groups = False


logger = logging.getLogger(__name__)


@login_required
def index(request):
    return redirect('authentication:dashboard')


def dashboard_groups(request):
    groups = request.user.groups.all()
    if _has_auto_groups:
        groups = groups\
            .filter(managedalliancegroup__isnull=True)\
            .filter(managedcorpgroup__isnull=True)
    groups = groups.order_by('name')

    context = {
        'groups': groups,
    }
    return render_to_string('authentication/dashboard_groups.html', context=context, request=request)


def dashboard_characters(request):
    characters = EveCharacter.objects\
        .filter(character_ownership__user=request.user)\
        .select_related()\
        .order_by('character_name')

    context = {
        'characters': characters
    }
    return render_to_string('authentication/dashboard_characters.html', context=context, request=request)


def dashboard_admin(request):
    if request.user.is_superuser:
        return render_to_string('allianceauth/admin-status/include.html', request=request)
    else:
        return ""


def dashboard_esi_check(request):
    if request.user.is_superuser:
        return render_to_string('allianceauth/admin-status/esi_check.html', request=request)
    else:
        return ""


@login_required
def dashboard(request):
    _dash_items = list()
    hooks = get_hooks('dashboard_hook')
    items = [fn() for fn in hooks]
    items.sort(key=lambda i: i.order)
    for item in items:
        _dash_items.append(item.render(request))

    context = {
        'views': _dash_items,
    }
    return render(request, 'authentication/dashboard.html', context)


@login_required
def token_management(request):
    tokens = request.user.token_set.all()

    context = {
        'tokens': tokens
    }
    return render(request, 'authentication/tokens.html', context)


@login_required
def token_delete(request, token_id=None):
    try:
        token = Token.objects.get(id=token_id)
        if request.user == token.user:
            token.delete()
            messages.success(request, "Token Deleted.")
        else:
            messages.error(request, "This token does not belong to you.")
    except Token.DoesNotExist:
        messages.warning(request, "Token does not exist")
    return redirect('authentication:token_management')


@login_required
def token_refresh(request, token_id=None):
    try:
        token = Token.objects.get(id=token_id)
        if request.user == token.user:
            try:
                token.refresh()
                messages.success(request, "Token refreshed.")
            except Exception as e:
                messages.warning(request, f"Failed to refresh token. {e}")
        else:
            messages.error(request, "This token does not belong to you.")
    except Token.DoesNotExist:
        messages.warning(request, "Token does not exist")
    return redirect('authentication:token_management')


@login_required
@token_required(scopes=settings.LOGIN_TOKEN_SCOPES)
def main_character_change(request, token):
    logger.debug(
        f"main_character_change called by user {request.user} for character {token.character_name}")
    try:
        co = CharacterOwnership.objects.get(
            character__character_id=token.character_id, user=request.user)
    except CharacterOwnership.DoesNotExist:
        if not CharacterOwnership.objects.filter(character__character_id=token.character_id).exists():
            co = CharacterOwnership.objects.create_by_token(token)
        else:
            messages.error(
                request,
                _('Cannot change main character to %(char)s: character owned by a different account.') % (
                    {'char': token.character_name})
            )
            co = None
    if co:
        request.user.profile.main_character = co.character
        request.user.profile.save(update_fields=['main_character'])
        messages.success(request, _('Changed main character to %s') % co.character)
        logger.info(
            'Changed user {user} main character to {char}'.format(
                user=request.user, char=co.character
            )
        )
    return redirect("authentication:dashboard")


@token_required(new=True, scopes=settings.LOGIN_TOKEN_SCOPES)
def add_character(request, token):
    if CharacterOwnership.objects.filter(character__character_id=token.character_id).filter(
            owner_hash=token.character_owner_hash).filter(user=request.user).exists():
        messages.success(request, _(
            'Added %(name)s to your account.' % ({'name': token.character_name})))
    else:
        messages.error(request, _('Failed to add %(name)s to your account: they already have an account.' % (
            {'name': token.character_name})))
    return redirect('authentication:dashboard')


"""
Override the HMAC two-step registration view to accommodate the three-step registration required.
Step 1: OAuth token to create user and profile.
Step 2: Get email and send activation link (but do not save email).
Step 3: Get link, save email and activate.

Step 1 is necessary to automatically assign character ownership and a main character, both of which require a saved User
model - this means the ensuing registration form cannot create the user because it already exists.

Email is not saved to the user model in Step 2 as a way of differentiating users who have not yet completed registration
(is_active=False) and users who have been disabled by an admin (is_active=False, email present).

Because of this, the email address needs to be assigned in Step 3 after clicking the link, which means the link must
have the email address embedded much like the username. Key creation and decoding is overridden to support this action.
"""


# Step 1
@token_required(new=True, scopes=settings.LOGIN_TOKEN_SCOPES)
def sso_login(request, token):
    user = authenticate(token=token)
    if user:
        token.user = user
        if Token.objects.exclude(pk=token.pk).equivalent_to(token).require_valid().exists():
            token.delete()
        else:
            token.save()
        if user.is_active:
            login(request, user)
            return redirect(request.POST.get('next', request.GET.get('next', 'authentication:dashboard')))
        elif not user.email:
            # Store the new user PK in the session to enable us to identify the registering user in Step 2
            request.session['registration_uid'] = user.pk
            # Go to Step 2
            return redirect('registration_register')
    # Logging in with an alt is not allowed due to security concerns.
    token.delete()
    messages.error(
        request,
        _(
            'Unable to authenticate as the selected character. '
            'Please log in with the main character associated with this account.'
        )
    )
    return redirect(settings.LOGIN_URL)


# Step 2
class RegistrationView(BaseRegistrationView):
    form_class = RegistrationForm
    template_name = "public/register.html"
    email_body_template = "registration/activation_email.txt"
    email_body_template_html = "registration/activation_email_html.txt"
    email_subject_template = "registration/activation_email_subject.txt"
    success_url = reverse_lazy('registration_complete')

    def send_activation_email(self, user):
        """
        Implement our own way to send a mail to make sure we
        send a RFC conform multipart email
        :param user:
        :type user:
        """

        activation_key = self.get_activation_key(user)
        context = self.get_email_context(activation_key)
        context["user"] = user

        # email subject
        subject = render_to_string(
            template_name=self.email_subject_template,
            context=context,
            request=self.request,
        )
        subject = "".join(subject.splitlines())

        # plaintext email body part
        message = render_to_string(
            template_name=self.email_body_template,
            context=context,
            request=self.request,
        )

        # html email body part
        message_html = render_to_string(
            template_name=self.email_body_template_html,
            context=context,
            request=self.request,
        )

        # send it
        user.email_user(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            **{'html_message': message_html},
        )

    def get_success_url(self, user):
        if not getattr(settings, 'REGISTRATION_VERIFY_EMAIL', True):
            return reverse_lazy('authentication:dashboard')
        return super().get_success_url(user)

    def dispatch(self, request, *args, **kwargs):
        # We're storing a key in the session to pass user information from OAuth response. Make sure it's there.
        if not self.request.session.get('registration_uid', None) or not User.objects.filter(
                pk=self.request.session.get('registration_uid')).exists():
            messages.error(self.request, _('Registration token has expired.'))
            return redirect(settings.LOGIN_URL)
        if not getattr(settings, 'REGISTRATION_VERIFY_EMAIL', True):
            # Keep the request so the user can be automagically logged in.
            setattr(self, 'request', request)
        return super().dispatch(request, *args, **kwargs)

    def register(self, form):
        user = User.objects.get(
            pk=self.request.session.get('registration_uid'))
        user.email = form.cleaned_data['email']
        user_registered.send(self.__class__, user=user, request=self.request)
        if getattr(settings, 'REGISTRATION_VERIFY_EMAIL', True):
            # Go to Step 3
            self.send_activation_email(user)
        else:
            user.is_active = True
            user.save()
            login(self.request, user, 'allianceauth.authentication.backends.StateBackend')
        return user

    def get_activation_key(self, user):
        return signing.dumps(obj=[getattr(user, User.USERNAME_FIELD), user.email], salt=REGISTRATION_SALT)

    def get_email_context(self, activation_key):
        context = super().get_email_context(activation_key)
        context['url'] = context['site'].domain + \
            reverse('registration_activate', args=[activation_key])
        return context


# Step 3
class ActivationView(BaseActivationView):
    template_name = "registration/activate.html"
    success_url = reverse_lazy('registration_activation_complete')

    def validate_key(self, activation_key):
        try:
            dump = signing.loads(
                activation_key,
                salt=REGISTRATION_SALT,
                max_age=settings.ACCOUNT_ACTIVATION_DAYS * 86400
            )
            return dump
        except signing.BadSignature:
            return None

    def activate(self, *args, **kwargs):
        dump = self.validate_key(kwargs.get('activation_key'))
        if dump:
            user = self.get_user(dump[0])
            if user:
                user.email = dump[1]
                user.is_active = True
                user.save()
                return user
        return False


def registration_complete(request):
    messages.success(request, _(
        'Sent confirmation email. Please follow the link to confirm your email address.'))
    return redirect('authentication:login')


def activation_complete(request):
    messages.success(request, _(
        'Confirmed your email address. Please login to continue.'))
    return redirect('authentication:dashboard')


def registration_closed(request):
    messages.error(request, _(
        'Registration of new accounts is not allowed at this time.'))
    return redirect('authentication:login')


@user_passes_test(lambda u: u.is_superuser)
def task_counts(request) -> JsonResponse:
    """Return task counts as JSON for an AJAX call."""
    data = _celery_stats()
    data.update(
        {"tasks_running": active_tasks_count(), "tasks_queued": queued_tasks_count()}
    )
    return JsonResponse(data)


def check_for_override_esi_error_message(response):
    if response.status_code in ESI_ERROR_MESSAGE_OVERRIDES:
        return {"error": ESI_ERROR_MESSAGE_OVERRIDES.get(response.status_code)}
    else:
        return response.json()


@user_passes_test(lambda u: u.is_superuser)
def esi_check(request) -> JsonResponse:
    """Return if ESI ok With error messages and codes as JSON"""
    _r = requests.get("https://esi.evetech.net/latest/status/?datasource=tranquility")

    data = {
        "status": _r.status_code,
        "data": check_for_override_esi_error_message(_r)
    }
    return JsonResponse(data)


@login_required
def dashboard_bs3(request):
    """Render dashboard view with BS3 theme.

    This is an internal view used for testing BS3 backward compatibility in AA4 only.
    """
    return render(request, 'authentication/dashboard_bs3.html')
