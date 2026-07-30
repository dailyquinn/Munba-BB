from django.urls import include, path

from . import views

app_name = 'ips4'

module_urls = [
    # IPS4 Service Control
    path('activate/', views.activate_ips4, name='activate'),
    path('deactivate/', views.deactivate_ips4, name='deactivate'),
    path('reset_password/', views.reset_ips4_password, name='reset_password'),
    path('set_password/', views.set_ips4_password, name='set_password'),
]

urlpatterns = [
    path('ips4/', include((module_urls, app_name), namespace=app_name))
]
