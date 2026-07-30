from django.urls import path

from . import views

app_name = 'timerboard'

urlpatterns = [
    path('', views.TimerView.as_view(), name='view'),
    path('add/', views.AddTimerView.as_view(), name='add'),
    path('remove/<int:pk>/', views.RemoveTimerView.as_view(), name='delete'),
    path('edit/<int:pk>/', views.EditTimerView.as_view(), name='edit'),
]
