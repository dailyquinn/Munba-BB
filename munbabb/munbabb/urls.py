from django.contrib import admin
from django.urls import path, include

from django.views.generic import TemplateView

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html')),
    path('index.html', TemplateView.as_view(template_name='index.html')),
    path('contracts.html', TemplateView.as_view(template_name='contracts.html')),
    path('', include('api.urls')),
] + static('/Scripts/', document_root=settings.BASE_DIR.parent / 'Scripts') \
  + static('/Media/', document_root=settings.BASE_DIR.parent / 'Media') \
  + static('/jsons/', document_root=settings.BASE_DIR.parent / 'jsons')
