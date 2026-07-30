from django.urls import include, path

from . import views

app_name = 'mumble'

module_urls = [
    # Mumble service control
    path('activate/', views.CreateAccountMumbleView.as_view(), name='activate'),
    path('deactivate/', views.DeleteMumbleView.as_view(), name='deactivate'),
    path('reset_password/', views.ResetPasswordMumbleView.as_view(), name='reset_password'),
    path('set_password/', views.SetPasswordMumbleView.as_view(), name='set_password'),
    path('connection_history/', views.connection_history, name="connection_history"),
    path('ajax/connection_history_data', views.connection_history_data, name="connection_history_data"),
    path('ajax/release_counts_data', views.release_counts_data, name="release_counts_data"),
    path('ajax/release_pie_chart_data', views.release_pie_chart_data, name="release_pie_chart_data"),
]

urlpatterns = [
    path('mumble/', include((module_urls, app_name), namespace=app_name))
]
