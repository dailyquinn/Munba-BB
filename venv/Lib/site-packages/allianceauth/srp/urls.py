from django.urls import path

from . import views

app_name = 'srp'

urlpatterns = [
    # SRP URLS
    path('', views.srp_management, name='management'),
    path('all/', views.srp_management, {'all': True}, name='all'),
    path('<int:fleet_id>/view/', views.srp_fleet_view, name='fleet'),
    path('add/', views.srp_fleet_add_view, name='add'),
    path('<int:fleet_id>/edit/', views.srp_fleet_edit_view, name='edit'),
    path('<str:fleet_srp>/request/', views.srp_request_view, name='request'),

    # SRP URLS
    path('<int:fleet_id>/remove/', views.srp_fleet_remove, name='remove'),
    path('<int:fleet_id>/disable/', views.srp_fleet_disable, name='disable'),
    path('<int:fleet_id>/enable/', views.srp_fleet_enable, name='enable'),
    path('<int:fleet_id>/complete/', views.srp_fleet_mark_completed,
        name='mark_completed'),
    path('<int:fleet_id>/incomplete/', views.srp_fleet_mark_uncompleted,
        name='mark_uncompleted'),
    path('request/remove/', views.srp_request_remove,
        name="request_remove"),
    path('request/approve/', views.srp_request_approve,
        name='request_approve'),
    path('request/reject/', views.srp_request_reject,
        name='request_reject'),
    path('request/<int:fleet_srp_request_id>/update/', views.srp_request_update_amount,
        name="request_update_amount"),
]
