from django.urls import path
from reporting.api import ActivityReportView, DashboardView

urlpatterns = [path('dashboard', DashboardView.as_view(), name='dashboard'),
               path('reports', ActivityReportView.as_view(), name='activity-report')]
