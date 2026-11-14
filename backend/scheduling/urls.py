from django.urls import path

from .api.appointments import AppointmentCollectionView
from .api.camps import CampCollectionView, CampDetailView
from .api.slots import SlotCollectionView

urlpatterns = [
    path('camps', CampCollectionView.as_view(), name='camp-collection'),
    path('camps/<uuid:camp_id>', CampDetailView.as_view(), name='camp-detail'),
    path('appointment-slots', SlotCollectionView.as_view(), name='slot-collection'),
    path('appointments', AppointmentCollectionView.as_view(), name='appointment-collection'),
]
