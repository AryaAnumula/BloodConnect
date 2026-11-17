from django.urls import path
from reporting.api.dashboard import DashboardView

urlpatterns = [path('dashboard', DashboardView.as_view(), name='dashboard')]
