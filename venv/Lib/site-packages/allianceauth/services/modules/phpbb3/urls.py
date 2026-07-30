from django.urls import include, path

from . import views

app_name = 'phpbb3'

module_urls = [
    # Forum Service Control
    path('activate/', views.activate_forum, name='activate'),
    path('deactivate/', views.deactivate_forum, name='deactivate'),
    path('reset_password/', views.reset_forum_password, name='reset_password'),
    path('set_password/', views.set_forum_password, name='set_password'),
]

urlpatterns = [
    path('phpbb3/', include((module_urls, app_name), namespace=app_name))
]
