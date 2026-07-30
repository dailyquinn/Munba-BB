from django.urls import include
from allianceauth.hooks import get_hooks
from django.urls import path

from . import views

urlpatterns = [
    # Services
    path('services/', include(([
        path('', views.services_view, name='services'),
        # Tools
        path('tool/fleet_formatter_tool/', views.fleet_formatter_view, name='fleet_format_tool'),
    ], 'services'), namespace='services')),
]

# Append hooked service urls
services = get_hooks('services_hook')
for svc in services:
    urlpatterns += svc().urlpatterns
