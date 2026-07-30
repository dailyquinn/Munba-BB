from django.urls import path
from . import views

app_name = "groupmanagement"

urlpatterns = [
    # groups
    path("groups/", views.groups_view, name="groups"),
    path("group/request/join/<int:group_id>/", views.group_request_add, name="request_add"),
    path(
        "group/request/leave/<int:group_id>/", views.group_request_leave, name="request_leave"
    ),
    path(
        "group/request/retract/<int:group_id>/",
        views.group_request_retract,
        name="request_retract"
    ),
    # group management
    path("groupmanagement/requests/", views.group_management, name="management"),
    path("groupmanagement/membership/", views.group_membership, name="membership"),
    path(
        "groupmanagement/membership/<int:group_id>/",
        views.group_membership_list,
        name="membership",
    ),
    path(
        "groupmanagement/membership/<int:group_id>/audit-log/",
        views.group_membership_audit,
        name="audit_log",
    ),
    path(
        "groupmanagement/membership/<int:group_id>/remove/<int:user_id>/",
        views.group_membership_remove,
        name="membership_remove",
    ),
    path(
        "groupmanagement/request/join/accept/<int:group_request_id>/",
        views.group_accept_request,
        name="accept_request",
    ),
    path(
        "groupmanagement/request/join/reject/<int:group_request_id>/",
        views.group_reject_request,
        name="reject_request",
    ),
    path(
        "groupmanagement/request/leave/accept/<int:group_request_id>/",
        views.group_leave_accept_request,
        name="leave_accept_request",
    ),
    path(
        "groupmanagement/request/leave/reject/<int:group_request_id>/",
        views.group_leave_reject_request,
        name="leave_reject_request",
    ),
]
