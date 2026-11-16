"""Isolated route composition; central config.urls is owned by Arya."""
from django.urls import include, path
urlpatterns = [path('api/v1/', include('inventory.urls')), path('', include('inventory.page_urls'))]
