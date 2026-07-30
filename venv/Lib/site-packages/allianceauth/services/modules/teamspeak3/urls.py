from django.urls import include, path

from . import views

app_name = 'teamspeak3'

module_urls = [
    # Teamspeak3 service control
    path('activate/', views.activate_teamspeak3, name='activate'),
    path('deactivate/', views.deactivate_teamspeak3, name='deactivate'),
    path('reset_perm/', views.reset_teamspeak3_perm, name='reset_perm'),
    path(
        'admin_update_ts3_groups/',
        views.admin_update_ts3_groups,
        name='admin_update_ts3_groups'
    ),

    # Teamspeak Urls
    path('verify/', views.verify_teamspeak3, name='verify'),
]

urlpatterns = [
    path('teamspeak3/', include((module_urls, app_name), namespace=app_name)),
]
