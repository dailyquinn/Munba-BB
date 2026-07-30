from django.urls import include, path

from . import views

app_name = 'smf'

module_urls = [
    # SMF Service Control
    path('activate/', views.activate_smf, name='activate'),
    path('deactivate/', views.deactivate_smf, name='deactivate'),
    path('reset_password/', views.reset_smf_password, name='reset_password'),
    path('set_password/', views.set_smf_password, name='set_password'),
]

urlpatterns = [
    path('smf/', include((module_urls, app_name), namespace=app_name)),
]
