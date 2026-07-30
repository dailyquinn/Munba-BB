from django.urls import re_path
from django.urls import path

from . import views

app_name = 'permissions_tool'

urlpatterns = [
    path('overview/', views.permissions_overview, name='overview'),
    re_path(r'^audit/(?P<app_label>[\w\-_]+)/(?P<model>[\w\-_]+)/(?P<codename>[\w\-_]+)/$', views.permissions_audit,
        name='audit'),
]
