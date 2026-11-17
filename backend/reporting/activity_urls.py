from django.urls import path
from reporting.api.activity import ActivityReportView

urlpatterns = [path('reports', ActivityReportView.as_view(), name='reports')]
