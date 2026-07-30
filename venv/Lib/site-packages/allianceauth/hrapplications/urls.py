from django.urls import path

from . import views

app_name = 'hrapplications'

urlpatterns = [
    path('', views.hr_application_management_view,
        name="index"),
    path('create/', views.hr_application_create_view,
        name="create_view"),
    path('create/<int:form_id>/', views.hr_application_create_view,
        name="create_view"),
    path('remove/<int:app_id>/', views.hr_application_remove,
        name="remove"),
    path('view/<int:app_id>/', views.hr_application_view,
        name="view"),
    path('personal/view/<int:app_id>/', views.hr_application_personal_view,
        name="personal_view"),
    path('personal/removal/<int:app_id>/',
        views.hr_application_personal_removal,
        name="personal_removal"),
    path('approve/<int:app_id>/', views.hr_application_approve,
        name="approve"),
    path('reject/<int:app_id>/', views.hr_application_reject,
        name="reject"),
    path('search/', views.hr_application_search,
        name="search"),
    path('mark_in_progress/<int:app_id>/', views.hr_application_mark_in_progress,
        name="mark_in_progress"),
]
