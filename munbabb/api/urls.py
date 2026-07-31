from django.urls import path
from . import views

urlpatterns = [
    path('api/config', views.get_config, name='get_config'),
    path('api/quote', views.add_quote, name='add_quote'),
    path('api/quote/', views.add_quote),
    path('api/quotes', views.add_quote),
    path('api/quotes/', views.add_quote),
    path('api/quote/<str:code>', views.get_quote, name='get_quote'),
    path('api/quotes/<str:code>', views.get_quote),
    path('api/save-multipliers', views.save_multipliers, name='save_multipliers'),
    path('api/sde/search', views.sde_search, name='sde_search'),
    path('api/sde/names', views.sde_names, name='sde_names'),
    path('api/sde/resolve_items', views.sde_resolve_items, name='sde_resolve_items'),
    path('fetch_contracts/', views.fetch_contracts, name='fetch_contracts'),
    path('login', views.login, name='login'),
    path('callback', views.callback, name='callback'),
    path('api/callback_token', views.api_callback_token, name='api_callback_token'),
]
