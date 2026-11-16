from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.validation import ISODateField, StrictInputSerializer
from reporting.permissions import IsReportingAdmin
from reporting.selectors.activity import activity_report


class ReportQuery(StrictInputSerializer):
    def get_fields(self):
        return {'from': ISODateField(), 'to': ISODateField()}


class ActivityReportView(APIView):
    permission_classes = [IsAuthenticated, IsReportingAdmin]

    def get(self, request):
        query = ReportQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(activity_report(actor=request.user, from_date=query.validated_data['from'],
                                        to_date=query.validated_data['to']))
