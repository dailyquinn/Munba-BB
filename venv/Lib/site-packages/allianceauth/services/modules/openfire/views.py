import datetime
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from allianceauth.services.forms import ServicePasswordForm

from .forms import JabberBroadcastForm
from .manager import OpenfireManager, PingBotException
from .models import OpenfireUser
from .tasks import OpenfireTasks

logger = logging.getLogger(__name__)

ACCESS_PERM = 'openfire.access_openfire'


@login_required
@permission_required(ACCESS_PERM)
def activate_jabber(request):
    logger.debug("activate_jabber called by user %s" % request.user)
    character = request.user.profile.main_character
    logger.debug(f"Adding Jabber user for user {request.user} with main character {character}")
    info = OpenfireManager.add_user(OpenfireTasks.get_username(request.user))
    # If our username is blank means we already had a user
    if info[0] != "":
        OpenfireUser.objects.update_or_create(user=request.user, defaults={'username': info[0]})
        logger.debug("Updated authserviceinfo for user %s with Jabber credentials. Updating groups." % request.user)
        OpenfireTasks.update_groups.delay(request.user.pk)
        logger.info("Successfully activated Jabber for user %s" % request.user)
        messages.success(request, _('Activated Jabber account.'))
        credentials = {
            'username': info[0],
            'password': info[1],
        }
        return render(request, 'services/service_credentials.html', context={'credentials': credentials, 'service': 'Jabber'})
    else:
        logger.error("Unsuccessful attempt to activate Jabber for user %s" % request.user)
        messages.error(request, _('An error occurred while processing your Jabber account.'))
    return redirect("services:services")


@login_required
@permission_required(ACCESS_PERM)
def deactivate_jabber(request):
    logger.debug("deactivate_jabber called by user %s" % request.user)
    if OpenfireTasks.has_account(request.user) and OpenfireTasks.delete_user(request.user):
        logger.info("Successfully deactivated Jabber for user %s" % request.user)
        messages.success(request, 'Deactivated Jabber account.')
    else:
        logger.error("Unsuccessful attempt to deactivate Jabber for user %s" % request.user)
        messages.error(request, _('An error occurred while processing your Jabber account.'))
    return redirect("services:services")


@login_required
@permission_required(ACCESS_PERM)
def reset_jabber_password(request):
    logger.debug("reset_jabber_password called by user %s" % request.user)
    if OpenfireTasks.has_account(request.user):
        result = OpenfireManager.update_user_pass(request.user.openfire.username)
        # If our username is blank means we failed
        if result != "":
            logger.info("Successfully reset Jabber password for user %s" % request.user)
            messages.success(request, _('Reset Jabber password.'))
            credentials = {
                'username': request.user.openfire.username,
                'password': result,
            }
            return render(request, 'services/service_credentials.html', context={'credentials': credentials, 'service': 'Jabber'})
    logger.error("Unsuccessful attempt to reset Jabber for user %s" % request.user)
    messages.error(request, _('An error occurred while processing your Jabber account.'))
    return redirect("services:services")


@login_required
@permission_required('auth.jabber_broadcast')
def jabber_broadcast_view(request):
    logger.debug("jabber_broadcast_view called by user %s" % request.user)
    allchoices = []
    if request.user.has_perm('auth.jabber_broadcast_all'):
        allchoices.append(('all', 'all'))
        for g in Group.objects.all():
            allchoices.append((str(g.name), str(g.name)))
    else:
        for g in request.user.groups.all():
            allchoices.append((str(g.name), str(g.name)))
    if request.method == 'POST':
        form = JabberBroadcastForm(request.POST)
        form.fields['group'].choices = allchoices
        logger.debug("Received POST request containing form, valid: %s" % form.is_valid())
        if form.is_valid():
            main_char = request.user.profile.main_character
            logger.debug(f"Processing Jabber broadcast for user {request.user} with main character {main_char}")
            try:
                if main_char is not None:
                    message_to_send = form.cleaned_data['message'] + "\n##### SENT BY: " + "[" + main_char.corporation_ticker + "]" + \
                                        main_char.character_name + " TO: " + \
                                        form.cleaned_data['group'] + " WHEN: " + datetime.datetime.now(datetime.timezone.utc).strftime(
                                            "%Y-%m-%d %H:%M:%S") + " #####\n##### Replies are NOT monitored #####\n"
                    group_to_send = form.cleaned_data['group']

                else:
                    message_to_send = form.cleaned_data['message'] + "\n##### SENT BY: " + "No character but can send pings?" + " TO: " + \
                                        form.cleaned_data['group'] + " WHEN: " + datetime.datetime.now(datetime.timezone.utc).strftime(
                                            "%Y-%m-%d %H:%M:%S") + " #####\n##### Replies are NOT monitored #####\n"
                    group_to_send = form.cleaned_data['group']

                OpenfireManager.send_broadcast_message(group_to_send, message_to_send)

                messages.success(request, _('Sent Jabber broadcast to %s' % group_to_send))
                logger.info("Sent Jabber broadcast on behalf of user %s" % request.user)
            except PingBotException as e:
                messages.error(request, e)

    else:
        form = JabberBroadcastForm()
        form.fields['group'].choices = allchoices
        logger.debug("Generated broadcast form for user {} containing {} groups".format(
            request.user, len(form.fields['group'].choices)))

    context = {'form': form}
    return render(request, 'services/openfire/broadcast.html', context=context)


@login_required
@permission_required(ACCESS_PERM)
def set_jabber_password(request):
    logger.debug("set_jabber_password called by user %s" % request.user)
    if request.method == 'POST':
        logger.debug("Received POST request with form.")
        form = ServicePasswordForm(request.POST)
        logger.debug("Form is valid: %s" % form.is_valid())
        if form.is_valid() and OpenfireTasks.has_account(request.user):
            password = form.cleaned_data['password']
            logger.debug("Form contains password of length %s" % len(password))
            result = OpenfireManager.update_user_pass(request.user.openfire.username, password=password)
            if result != "":
                logger.info("Successfully set Jabber password for user %s" % request.user)
                messages.success(request, _('Set jabber password.'))
            else:
                logger.error("Failed to install custom Jabber password for user %s" % request.user)
                messages.error(request, _('An error occurred while processing your Jabber account.'))
            return redirect("services:services")
    else:
        logger.debug("Request is not type POST - providing empty form.")
        form = ServicePasswordForm()

    logger.debug("Rendering form for user %s" % request.user)
    context = {'form': form, 'service': 'Jabber'}
    return render(request, 'services/service_password.html', context=context)
