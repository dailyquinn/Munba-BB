import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .form import OpForm
from .models import OpTimer, OpTimerType

logger = logging.getLogger(__name__)

OPS_VIEW_PERMISSION = 'auth.optimer_view'
OPS_MANAGE_PERMISSION = 'auth.optimer_management'

@login_required
@permission_required(OPS_VIEW_PERMISSION)
def optimer_view(request):
    """
    View for the optimer management page

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.debug("optimer_view called by user %s" % request.user)
    base_query = OpTimer.objects.select_related('eve_character', 'type')
    render_items = {'optimer': base_query.all(),
                    'future_timers': base_query.filter(
                        start__gte=timezone.now()),
                    'past_timers': base_query.filter(
                        start__lt=timezone.now()).order_by('-start')}

    return render(request, 'optimer/management.html', context=render_items)


@login_required
@permission_required(OPS_MANAGE_PERMISSION)
def add_optimer_view(request):
    """
    View for the add optimer page

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.debug("add_optimer_view called by user %s" % request.user)

    if request.method == 'POST':
        form = OpForm(request.POST, data_list=OpTimerType.objects.all())
        logger.debug("Request type POST contains form valid: %s" % form.is_valid())
        if form.is_valid():
            optimer_type = None

            if form.cleaned_data['type'] != '':
                try:
                    optimer_type = OpTimerType.objects.get(
                        type__iexact=form.cleaned_data['type']
                    )
                except OpTimerType.DoesNotExist:
                    optimer_type = OpTimerType.objects.create(
                        type=form.cleaned_data['type']
                    )

            # Get Current Time
            post_time = timezone.now()
            # Get character
            character = request.user.profile.main_character
            # handle valid form
            op = OpTimer()
            op.doctrine = form.cleaned_data['doctrine']
            op.system = form.cleaned_data['system']
            op.start = form.cleaned_data['start']
            op.duration = form.cleaned_data['duration']
            op.operation_name = form.cleaned_data['operation_name']
            op.fc = form.cleaned_data['fc']
            op.create_time = post_time
            op.eve_character = character
            op.type = optimer_type
            op.description = form.cleaned_data['description']
            op.save()
            logger.info(f"User {request.user} created op timer with name {op.operation_name}")
            messages.success(request, _('Created operation timer for %(opname)s.') % {"opname": op.operation_name})
            return redirect("optimer:view")
    else:
        logger.debug("Returning new opForm")
        form = OpForm(data_list=OpTimerType.objects.all())

    render_items = {'form': form}

    return render(request, 'optimer/add.html', context=render_items)


@login_required
@permission_required(OPS_MANAGE_PERMISSION)
def remove_optimer(request, optimer_id):
    """
    Remove optimer

    :param request:
    :type request:
    :param optimer_id:
    :type optimer_id:
    :return:
    :rtype:
    """

    logger.debug(f"remove_optimer called by user {request.user} for operation id {optimer_id}")
    op = get_object_or_404(OpTimer, id=optimer_id)
    op.delete()
    logger.info(f"Deleting optimer id {optimer_id} by user {request.user}")
    messages.success(request, _('Removed operation timer for %(opname)s.') % {"opname": op.operation_name})

    return redirect("optimer:view")


@login_required
@permission_required(OPS_MANAGE_PERMISSION)
def edit_optimer(request, optimer_id):
    """
    Edit optimer

    :param request:
    :type request:
    :param optimer_id:
    :type optimer_id:
    :return:
    :rtype:
    """

    logger.debug(f"edit_optimer called by user {request.user} for optimer id {optimer_id}")
    op = get_object_or_404(OpTimer, id=optimer_id)

    if request.method == 'POST':
        form = OpForm(request.POST, data_list=OpTimerType.objects.all())
        logger.debug("Received POST request containing update optimer form, is valid: %s" % form.is_valid())
        if form.is_valid():
            character = request.user.profile.main_character

            optimer_type = None

            if form.cleaned_data['type'] != '':
                try:
                    optimer_type = OpTimerType.objects.get(
                        type__iexact=form.cleaned_data['type']
                    )
                except OpTimerType.DoesNotExist:
                    optimer_type = OpTimerType.objects.create(
                        type=form.cleaned_data['type']
                    )

            op.doctrine = form.cleaned_data['doctrine']
            op.system = form.cleaned_data['system']
            op.start = form.cleaned_data['start']
            op.duration = form.cleaned_data['duration']
            op.operation_name = form.cleaned_data['operation_name']
            op.fc = form.cleaned_data['fc']
            op.eve_character = character
            op.type = optimer_type
            op.description = form.cleaned_data['description']
            logger.info(f"User {request.user} updating optimer id {optimer_id} ")
            op.save()
            messages.success(request, _('Saved changes to operation timer for %(opname)s.') % {"opname": op.operation_name})
            return redirect("optimer:view")
    else:
        data = {
            'doctrine': op.doctrine,
            'system': op.system,
            'start': op.start,
            'duration': op.duration,
            'operation_name': op.operation_name,
            'fc': op.fc,
            'description': op.description,
            'type': op.type
        }
        form = OpForm(initial=data, data_list=OpTimerType.objects.all())
    return render(request, 'optimer/update.html', context={'form': form})


def dashboard_ops(request):
    """
    Returns the next five upcoming ops for the dashboard

    :param request:
    :type request:
    :return:
    :rtype:
    """
    if request.user.has_perm(OPS_VIEW_PERMISSION):
        base_query = OpTimer.objects.select_related('eve_character', 'type')
        timers = base_query.filter(
            start__gte=timezone.now()
        )[:5]

        if timers.count():
            context = {
                'timers': timers,
            }
            return render_to_string(
                'optimer/dashboard.ops.html',
                context=context,
                request=request
            )
        else:
            return ""
    else:
        return ""
