from django.urls import path
from . import views

app_name = 'corputils'
urlpatterns = [
    path('', views.corpstats_view, name='view'),
    path('add/', views.corpstats_add, name='add'),
    path('<int:corp_id>/', views.corpstats_view, name='view_corp'),
    path('<int:corp_id>/update/', views.corpstats_update, name='update'),
    path('search/', views.corpstats_search, name='search'),
]
