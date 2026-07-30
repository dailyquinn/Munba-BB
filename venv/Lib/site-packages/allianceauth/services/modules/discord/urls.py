from django.urls import include, path

from . import views

app_name = 'discord'

module_urls = [
    # Discord Service Control
    path('activate/', views.activate_discord, name='activate'),
    path('deactivate/', views.deactivate_discord, name='deactivate'),
    path('reset/', views.reset_discord, name='reset'),
    path('callback/', views.discord_callback, name='callback'),
    path('add_bot/', views.discord_add_bot, name='add_bot'),
]

urlpatterns = [
    path('discord/', include((module_urls, app_name), namespace=app_name))
]
