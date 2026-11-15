from django.urls import path

from blood_requests.api.create import RequestCreateView

urlpatterns = [
    path('requests', RequestCreateView.as_view(), name='request-create'),
]
