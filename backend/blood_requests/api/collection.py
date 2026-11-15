"""Shared collection /api/v1/requests with per-method role dispatch (BC-D029-e).

POST (BB-17): authenticated, active, non-superuser REQUESTER only, unchanged.
GET (BB-18 staff slice): authenticated, active, non-superuser STAFF -> staff_queue.
REQUESTER GET (own list) is BB-19, owned by Arya: until it exists, requesters get
403 forbidden, which is deliberately temporary, not a permanent role policy.
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import DecisionRequired, envelope
from core.parsers import StrictJSONParser

from blood_requests.permissions import IsRequester, IsReviewStaff
from blood_requests.selectors.review_queue import staff_queue
from blood_requests.serializers import StaffQueueQuerySerializer
from blood_requests.services.submission import submit_request


@method_decorator(csrf_protect, name='dispatch')
class RequestCollectionView(APIView):
    parser_classes = [StrictJSONParser]
    method_gates = {'POST': IsRequester, 'GET': IsReviewStaff}

    def get_permissions(self):
        gate = self.method_gates.get(self.request.method)
        return [IsAuthenticated()] + ([gate()] if gate else [])

    def get(self, request, *args, **kwargs):
        query = StaffQueueQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        return Response(staff_queue(actor=request.user, status=params.get('status'),
                                    page=params['page'], page_size=params['page_size']))

    def post(self, request, *args, **kwargs):
        try:
            payload = submit_request(actor=request.user, data=request.data)
        except DecisionRequired:
            return Response(envelope(request, 'policy_unresolved',
                                     'Blood requests cannot be accepted until the request policy is configured.'),
                            status=409)
        return Response(payload, status=201)
