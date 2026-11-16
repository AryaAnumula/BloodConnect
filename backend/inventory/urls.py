from django.urls import path
from inventory.api import BloodUnitIntake

app_name = 'inventory'
urlpatterns = [path('blood-units', BloodUnitIntake.as_view(), name='blood-unit-intake')]
