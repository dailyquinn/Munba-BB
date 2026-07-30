from allianceauth.authentication import views
from django.urls import include, re_path, path

urlpatterns = [
    path('activate/complete/', views.activation_complete, name='registration_activation_complete'),
    # The activation key can make use of any character from the
    # URL-safe base64 alphabet, plus the colon as a separator.
    re_path(r'^activate/(?P<activation_key>[-:\w]+)/$', views.ActivationView.as_view(), name='registration_activate'),
    path('register/', views.RegistrationView.as_view(), name='registration_register'),
    path('register/complete/', views.registration_complete, name='registration_complete'),
    path('register/closed/', views.registration_closed, name='registration_disallowed'),
    path('', include('django.contrib.auth.urls')),
]
