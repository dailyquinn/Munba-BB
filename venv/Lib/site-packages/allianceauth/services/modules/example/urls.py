from django.urls import include, path

app_name = 'example'

module_urls = [
    # Add your module URLs here
]

urlpatterns = [
    path('example/', include((module_urls, app_name), namespace=app_name)),
]
