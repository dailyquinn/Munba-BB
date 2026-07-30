from django.urls import path
from django.views.generic.base import TemplateView

from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'account/login/',
        TemplateView.as_view(template_name='public/login.html'),
        name='login'
    ),
    path(
        'account/characters/main/',
        views.main_character_change,
        name='change_main_character'
    ),
    path(
        'account/characters/add/',
        views.add_character,
        name='add_character'
    ),
    path(
        'account/tokens/manage/',
        views.token_management,
        name='token_management'
    ),
    path(
        'account/tokens/delete/<int:token_id>',
        views.token_delete,
        name='token_delete'
    ),
    path(
        'account/tokens/refresh/<int:token_id>',
        views.token_refresh,
        name='token_refresh'
    ),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard_bs3/', views.dashboard_bs3, name='dashboard_bs3'),
    path('task-counts/', views.task_counts, name='task_counts'),
    path('esi-check/', views.esi_check, name='esi_check'),
]
