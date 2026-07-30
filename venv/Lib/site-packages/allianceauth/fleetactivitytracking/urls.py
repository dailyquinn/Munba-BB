from django.urls import path

from . import views
app_name = 'fleetactivitytracking'

urlpatterns = [
    # FleetActivityTracking (FAT)
    path('', views.fatlink_view, name='view'),
    path('statistics/', views.fatlink_statistics_view, name='statistics'),
    path('statistics/corp/<int:corpid>/', views.fatlink_statistics_corp_view,
        name='statistics_corp'),
    path('statistics/corp/<int:corpid>/<int:year>/<int:month>/',
        views.fatlink_statistics_corp_view,
        name='statistics_corp_month'),
    path('statistics/<int:year>/<int:month>/', views.fatlink_statistics_view,
        name='statistics_month'),
    path('user/statistics/', views.fatlink_personal_statistics_view,
        name='personal_statistics'),
    path('user/statistics/<int:year>/', views.fatlink_personal_statistics_view,
        name='personal_statistics_year'),
    path('user/statistics/<int:year>/<int:month>/',
        views.fatlink_monthly_personal_statistics_view,
        name='personal_statistics_month'),
    path('user/<int:char_id>/statistics/<int:year>/<int:month>/',
        views.fatlink_monthly_personal_statistics_view,
        name='user_statistics_month'),
    path('create/', views.create_fatlink_view, name='create'),
    path('modify/<str:fat_hash>/', views.modify_fatlink_view, name='modify'),
    path('link/<str:fat_hash>/', views.click_fatlink_view, name='click'),
]
