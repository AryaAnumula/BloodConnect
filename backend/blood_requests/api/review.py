"""BB-18 PATCH /api/v1/requests/{request_id}/status (BC-D029-b/c).

Active non-superuser STAFF only; session + CSRF; StrictJSONParser. The body is validated
(including whether the rejection_reason key is present) before review_request runs.
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.parsers import StrictJSONParser

from blood_requests.permissions import IsReviewStaff
from blood_requests.serializers import ReviewDecisionSerializer
from blood_requests.services.review import review_request


@method_decorator(csrf_protect, name='dispatch')
class RequestReviewView(APIView):
    permission_classes = [IsAuthenticated, IsReviewStaff]
    parser_classes = [StrictJSONParser]

    def patch(self, request, request_id, *args, **kwargs):
        decision = ReviewDecisionSerializer(data=request.data)
        decision.is_valid(raise_exception=True)
        data = decision.validated_data
        return Response(review_request(actor=request.user, request_id=request_id,
                                       status=data['status'],
                                       rejection_reason=data['rejection_reason']))
