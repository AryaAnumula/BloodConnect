"""BB-16 POST /api/v1/requests/{request_id}/issues -> 201 IssueResponse (BC-D026).

Active non-superuser STAFF only; session + CSRF; StrictJSONParser; body exactly
{"unit_ids": [...]}. If the inventory provider module is absent this returns
503 inventory_unavailable and changes nothing.
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.parsers import StrictJSONParser

from blood_requests.permissions import IsIssueStaff
from blood_requests.serializers.issue import IssueCreateSerializer
from blood_requests.services.issue import issue_request


@method_decorator(csrf_protect, name='dispatch')
class RequestIssueView(APIView):
    permission_classes = [IsAuthenticated, IsIssueStaff]
    parser_classes = [StrictJSONParser]

    def post(self, request, request_id, *args, **kwargs):
        body = IssueCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(issue_request(actor=request.user, request_id=request_id,
                                      unit_ids=body.validated_data['unit_ids']), status=201)
