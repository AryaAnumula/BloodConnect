from django.urls import path
from inventory.pages import IntakePage, StockPage, AlertPage

app_name = 'inventory-pages'
urlpatterns = [path('staff/inventory/new', IntakePage.as_view(), name='intake'),
               path('staff/inventory', StockPage.as_view(), name='stock'),
               path('staff/inventory/alerts', AlertPage.as_view(), name='alerts')]
