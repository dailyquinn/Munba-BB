import logging

from allianceauth.services.forms import ServicePasswordModelForm
from allianceauth.services.abstract import BaseCreatePasswordServiceAccountView, BaseDeactivateServiceAccountView, \
    BaseResetPasswordServiceAccountView, BaseSetPasswordServiceAccountView
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from .models import MumbleUser

logger = logging.getLogger(__name__)


class MumblePasswordForm(ServicePasswordModelForm):
    class Meta:
        model = MumbleUser
        fields = ('password',)


class MumbleViewMixin:
    service_name = 'mumble'
    model = MumbleUser
    permission_required = 'mumble.access_mumble'


class CreateAccountMumbleView(MumbleViewMixin, BaseCreatePasswordServiceAccountView):
    pass


class DeleteMumbleView(MumbleViewMixin, BaseDeactivateServiceAccountView):
    pass


class ResetPasswordMumbleView(MumbleViewMixin, BaseResetPasswordServiceAccountView):
    pass


class SetPasswordMumbleView(MumbleViewMixin, BaseSetPasswordServiceAccountView):
    form_class = MumblePasswordForm


@login_required
@permission_required('mumble.view_connection_history')
def connection_history(request) -> HttpResponse:

    context = {
        "mumble_url": settings.MUMBLE_URL,
    }

    return render(request, 'services/mumble/mumble_connection_history.html', context)


@login_required
@permission_required("mumble.view_connection_history")
def connection_history_data(request) -> JsonResponse:
    connection_history_data = MumbleUser.objects.all(
    ).values(
        'user',
        'display_name',
        'release',
        'version',
        'last_connect',
        'last_disconnect',
    )

    return JsonResponse({"connection_history_data": list(connection_history_data)})


@login_required
@permission_required("mumble.view_connection_history")
def release_counts_data(request) -> JsonResponse:
    release_counts_data = MumbleUser.objects.values('release').annotate(user_count=Count('user_id')).order_by('release')

    return JsonResponse({
        "release_counts_data": list(release_counts_data),
    })


@login_required
@permission_required("mumble.view_connection_history")
def release_pie_chart_data(request) -> JsonResponse:
    release_counts = MumbleUser.objects.values('release').annotate(user_count=Count('user_id')).order_by('release')

    return JsonResponse({
        "labels": list(release_counts.values_list("release", flat=True)),
        "values": list(release_counts.values_list("user_count", flat=True)),
    })
