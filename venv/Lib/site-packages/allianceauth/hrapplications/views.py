import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect, Http404
from django.db.models import Q
from .models import Application
from .models import ApplicationComment
from .models import ApplicationForm
from .models import ApplicationResponse
from allianceauth.notifications import notify

from .forms import HRApplicationCommentForm
from .forms import HRApplicationSearchForm

logger = logging.getLogger(__name__)


def create_application_test(user):
    return bool(user.profile.main_character)


@login_required
def hr_application_management_view(request):
    logger.debug("hr_application_management_view called by user %s" % request.user)
    corp_applications = []
    finished_corp_applications = []
    main_char = request.user.profile.main_character

    base_app_query = Application.objects.select_related('user', 'form', 'form__corp')
    if request.user.is_superuser:
        corp_applications = base_app_query.filter(approved=None).order_by('-created')
        finished_corp_applications = base_app_query.exclude(approved=None).order_by('-created')
    elif request.user.has_perm('auth.human_resources') and main_char:
        if ApplicationForm.objects.filter(corp__corporation_id=main_char.corporation_id).exists():
            app_form = ApplicationForm.objects.get(corp__corporation_id=main_char.corporation_id)
            corp_applications = base_app_query.filter(form=app_form).filter(approved=None).order_by('-created')
            finished_corp_applications = base_app_query.filter(form=app_form).filter(
                approved__in=[True, False]).order_by('-created')
    logger.debug("Retrieved {} personal, {} corp applications for {}".format(
        len(request.user.applications.all()), len(corp_applications), request.user))
    context = {
        'personal_apps': request.user.applications.all(),
        'applications': corp_applications,
        'finished_applications': finished_corp_applications,
        'search_form': HRApplicationSearchForm(),
        'create': create_application_test(request.user)
    }
    return render(request, 'hrapplications/management.html', context=context)


@login_required
@user_passes_test(create_application_test)
def hr_application_create_view(request, form_id=None):
    if form_id:
        app_form = get_object_or_404(ApplicationForm, id=form_id)
        if request.method == "POST":
            if Application.objects.filter(user=request.user).filter(form=app_form).exists():
                logger.warning(f"User {request.user} attempting to duplicate application to {app_form.corp}")
            else:
                application = Application(user=request.user, form=app_form)
                application.save()
                for question in app_form.questions.all():
                    response = ApplicationResponse(question=question, application=application)
                    response.answer = "\n".join(request.POST.getlist(str(question.pk), ""))
                    response.save()
                logger.info(f"{request.user} created {application}")
            return redirect('hrapplications:personal_view', application.id)
        else:
            questions = app_form.questions.all()
            return render(request, 'hrapplications/create.html', context={'questions': questions, 'corp': app_form.corp})
    else:
        choices = []
        for app_form in ApplicationForm.objects.all():
            if not Application.objects.filter(user=request.user).filter(form=app_form).exists():
                choices.append((app_form.id, app_form.corp.corporation_name))
        return render(request, 'hrapplications/corpchoice.html', context={'choices': choices})


@login_required
def hr_application_personal_view(request, app_id):
    logger.debug(f"hr_application_personal_view called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if app.user == request.user:
        context = {
            'app': app,
            'responses': ApplicationResponse.objects.filter(application=app),
            'buttons': False,
            'comments': ApplicationComment.objects.filter(application=app),
            'comment_form': HRApplicationCommentForm(),
        }
        return render(request, 'hrapplications/view.html', context=context)
    else:
        logger.warning(f"User {request.user} not authorized to view {app}")
        return redirect('hrapplications:personal_view')


@login_required
def hr_application_personal_removal(request, app_id):
    logger.debug(f"hr_application_personal_removal called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if app.user == request.user:
        if app.approved is None:
            logger.info(f"User {request.user} deleting {app}")
            app.delete()
        else:
            logger.warning(f"User {request.user} attempting to delete reviewed app {app}")
    else:
        logger.warning(f"User {request.user} not authorized to delete {app}")
    return redirect('hrapplications:index')


@login_required
@permission_required('auth.human_resources')
def hr_application_view(request, app_id):
    logger.debug(f"hr_application_view called by user {request.user} for app id {app_id}")
    try:
        app = Application.objects.prefetch_related('responses', 'comments', 'comments__user').get(pk=app_id)
    except Application.DoesNotExist:
        raise Http404
    if request.method == 'POST':
        if request.user.has_perm('hrapplications.add_applicationcomment'):
            form = HRApplicationCommentForm(request.POST)
            logger.debug("Request type POST contains form valid: %s" % form.is_valid())
            if form.is_valid():
                comment = ApplicationComment()
                comment.application = app
                comment.user = request.user
                comment.text = form.cleaned_data['comment']
                comment.save()
                logger.info(f"Saved comment by user {request.user} to {app}")
                return redirect('hrapplications:view', app_id)
        else:
            logger.warning("User %s does not have permission to add ApplicationComments" % request.user)
            return redirect('hrapplications:view', app_id)
    else:
        logger.debug("Returning blank HRApplication comment form.")
        form = HRApplicationCommentForm()
    context = {
        'app': app,
        'responses': app.responses.all(),
        'buttons': True,
        'comments': app.comments.all(),
        'comment_form': form,
    }
    return render(request, 'hrapplications/view.html', context=context)


@login_required
@permission_required('auth.human_resources')
@permission_required('hrapplications.delete_application')
def hr_application_remove(request, app_id):
    logger.debug(f"hr_application_remove called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    logger.info(f"User {request.user} deleting {app}")
    app.delete()
    notify(app.user, "Application Deleted", message="Your application to %s was deleted." % app.form.corp)
    return redirect('hrapplications:index')


@login_required
@permission_required('auth.human_resources')
@permission_required('hrapplications.approve_application')
def hr_application_approve(request, app_id):
    logger.debug(f"hr_application_approve called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if request.user.is_superuser or request.user == app.reviewer:
        logger.info(f"User {request.user} approving {app}")
        app.approved = True
        app.save()
        notify(app.user, "Application Accepted", message="Your application to %s has been approved." % app.form.corp, level="success")
    else:
        logger.warning(f"User {request.user} not authorized to approve {app}")
    return redirect('hrapplications:index')


@login_required
@permission_required('auth.human_resources')
@permission_required('hrapplications.reject_application')
def hr_application_reject(request, app_id):
    logger.debug(f"hr_application_reject called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if request.user.is_superuser or request.user == app.reviewer:
        logger.info(f"User {request.user} rejecting {app}")
        app.approved = False
        app.save()
        notify(app.user, "Application Rejected", message="Your application to %s has been rejected." % app.form.corp, level="danger")
    else:
        logger.warning(f"User {request.user} not authorized to reject {app}")
    return redirect('hrapplications:index')


@login_required
@permission_required('auth.human_resources')
def hr_application_search(request):
    logger.debug("hr_application_search called by user %s" % request.user)
    if request.method == 'POST':
        form = HRApplicationSearchForm(request.POST)
        logger.debug("Request type POST contains form valid: %s" % form.is_valid())
        if form.is_valid():
            searchstring = form.cleaned_data['search_string'].lower()
            applications = set()
            logger.debug(f"Searching for application with character name {searchstring} for user {request.user}")
            app_list = Application.objects.all()
            if not request.user.is_superuser:
                try:
                    app_list = app_list.filter(
                        form__corp__corporation_id=request.user.profile.main_character.corporation_id)
                except AttributeError:
                    logger.warning(
                        "User %s missing main character model: unable to filter applications to search" % request.user)

            applications = app_list.filter(
                Q(user__profile__main_character__character_name__icontains=searchstring) |
                Q(user__profile__main_character__corporation_name__icontains=searchstring) |
                Q(user__profile__main_character__alliance_name__icontains=searchstring) |
                Q(user__character_ownerships__character__character_name__icontains=searchstring) |
                Q(user__character_ownerships__character__corporation_name__icontains=searchstring) |
                Q(user__character_ownerships__character__alliance_name__icontains=searchstring) |
                Q(user__username__icontains=searchstring)
            ).distinct()

            context = {'applications': applications, 'search_form': HRApplicationSearchForm()}

            return render(request, 'hrapplications/searchview.html', context=context)
        else:
            logger.debug("Form invalid - returning for user %s to retry." % request.user)
            context = {'applications': None, 'search_form': form}
            return render(request, 'hrapplications/searchview.html', context=context)

    else:
        logger.debug("Returning empty search form for user %s" % request.user)
        return redirect("hrapplications:view")


@login_required
@permission_required('auth.human_resources')
def hr_application_mark_in_progress(request, app_id):
    logger.debug(f"hr_application_mark_in_progress called by user {request.user} for app id {app_id}")
    app = get_object_or_404(Application, pk=app_id)
    if not app.reviewer:
        logger.info(f"User {request.user} marking {app} in progress")
        app.reviewer = request.user
        app.reviewer_character = request.user.profile.main_character
        app.save()
        notify(app.user, "Application In Progress", message=f"Your application to {app.form.corp} is being reviewed by {app.reviewer_str}")
    else:
        logger.warning(
            f"User {request.user} unable to mark {app} in progress: already being reviewed by {app.reviewer}")
    return redirect("hrapplications:view", app_id)
