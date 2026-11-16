from django.urls import path

from blood_requests.api.collection import RequestCollectionView
from blood_requests.api.issue import RequestIssueView
from blood_requests.api.review import RequestReviewView

urlpatterns = [
    path('requests', RequestCollectionView.as_view(), name='request-collection'),
    path('requests/<uuid:request_id>/status', RequestReviewView.as_view(), name='request-review'),
    path('requests/<uuid:request_id>/issues', RequestIssueView.as_view(), name='request-issue'),
]
