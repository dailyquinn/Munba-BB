from django.urls import path

from . import views

urlpatterns = [
    # Discourse Service Control
    path('discourse/sso', views.discourse_sso, name='auth_discourse_sso'),
]
