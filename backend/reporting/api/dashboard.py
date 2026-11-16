from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.validation import StrictInputSerializer
from reporting.permissions import IsReportingAdmin
from reporting.selectors.dashboard import dashboard_for_admin


class EmptyQuery(StrictInputSerializer):
    pass


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsReportingAdmin]

    def get(self, request):
        query = EmptyQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(dashboard_for_admin(actor=request.user, now=timezone.now()))


