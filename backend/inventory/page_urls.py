from django.urls import path
from inventory.pages import IntakePage

app_name = 'inventory-pages'
urlpatterns = [path('staff/inventory/new', IntakePage.as_view(), name='intake')]
