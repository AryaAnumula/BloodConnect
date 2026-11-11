from django.urls import path

from .api.camps import CampCollectionView, CampDetailView

urlpatterns = [
    path('camps', CampCollectionView.as_view(), name='camp-collection'),
    path('camps/<uuid:camp_id>', CampDetailView.as_view(), name='camp-detail'),
]
