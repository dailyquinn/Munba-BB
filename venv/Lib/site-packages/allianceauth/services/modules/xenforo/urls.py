from django.urls import include, path

from . import views

app_name = 'xenforo'

module_urls = [
    # XenForo service control
    path('activate/', views.activate_xenforo_forum, name='activate'),
    path('deactivate/', views.deactivate_xenforo_forum, name='deactivate'),
    path('reset_password/', views.reset_xenforo_password, name='reset_password'),
    path('set_password/', views.set_xenforo_password, name='set_password'),
]

urlpatterns = [
    path('xenforo/', include((module_urls, app_name), namespace=app_name)),
]
