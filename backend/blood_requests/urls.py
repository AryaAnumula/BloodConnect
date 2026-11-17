from django.urls import path

from blood_requests.api.collection import RequestCollectionView
from blood_requests.api.issue import RequestIssueView
from blood_requests.api.review import RequestReviewView
from blood_requests.api.tracking import RequestCloseView, RequestDetailView

urlpatterns = [
    path('requests', RequestCollectionView.as_view(), name='request-collection'),
    path('requests/<uuid:request_id>/status', RequestReviewView.as_view(), name='request-review'),
    path('requests/<uuid:request_id>', RequestDetailView.as_view(), name='request-detail'),
    path('requests/<uuid:request_id>/close', RequestCloseView.as_view(), name='request-close'),


    path('requests/<uuid:request_id>/issues', RequestIssueView.as_view(), name='request-issue'),
]
