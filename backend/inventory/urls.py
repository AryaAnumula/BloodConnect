from django.urls import path
from inventory.api import BloodUnitIntake, UnitDetail, UnitDisposition, StockView, AlertView

app_name = 'inventory'
urlpatterns = [
    path('blood-units', BloodUnitIntake.as_view(), name='blood-unit-intake'),
    path('blood-units/<uuid:unit_id>', UnitDetail.as_view(), name='blood-unit-detail'),
    path('blood-units/<uuid:unit_id>/dispositions', UnitDisposition.as_view(), name='disposition'),
    path('stock', StockView.as_view(), name='stock'),
    path('stock/alerts', AlertView.as_view(), name='alerts'),
]
