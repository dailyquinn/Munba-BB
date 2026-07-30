from django.urls import path

from . import views

app_name = 'optimer'

urlpatterns = [
    path('', views.optimer_view, name='view'),
    path('add/', views.add_optimer_view, name='add'),
    path('<int:optimer_id>/remove/', views.remove_optimer, name='remove'),
    path('<int:optimer_id>/edit/', views.edit_optimer, name='edit'),
]
