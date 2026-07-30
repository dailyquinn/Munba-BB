from django.urls import include, path

from . import views

app_name = 'openfire'

module_urls = [
    # Jabber Service Control
    path('activate/', views.activate_jabber, name='activate'),
    path('deactivate/', views.deactivate_jabber, name='deactivate'),
    path('reset_password/', views.reset_jabber_password, name='reset_password'),
    path('set_password/', views.set_jabber_password, name='set_password'),
    path('broadcast/', views.jabber_broadcast_view, name='broadcast'),
]

urlpatterns = [
    path('openfire/', include((module_urls, app_name), namespace=app_name)),
]
