"""BB-17 POST /api/v1/requests -> 201 BloodRequest. Owner: Arnav.

Session authentication + CSRF (csrf_protect), StrictJSONParser, requester gate before any
work. Anonymous: 403 authentication_required; wrong role/inactive/superuser: 403 forbidden
(one audit event via core.errors). Missing/invalid policy: 409 policy_unresolved.
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import DecisionRequired, envelope
from core.parsers import StrictJSONParser

from blood_requests.permissions import IsRequester
from blood_requests.services.submission import submit_request


@method_decorator(csrf_protect, name='dispatch')
class RequestCreateView(APIView):
    permission_classes = [IsAuthenticated, IsRequester]
    parser_classes = [StrictJSONParser]

    def post(self, request, *args, **kwargs):
        try:
            payload = submit_request(actor=request.user, data=request.data)
        except DecisionRequired:
            return Response(envelope(request, 'policy_unresolved',
                                     'Blood requests cannot be accepted until the request policy is configured.'),
                            status=409)
        return Response(payload, status=201)
