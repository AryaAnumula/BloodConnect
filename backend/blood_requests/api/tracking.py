"""BB-19 minimized detail and dedicated no-body owner-only close action."""
from django.utils.decorators import method_decorator
from django.http import RawPostDataException
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from blood_requests.permissions import IsRequester, IsRequestReader
from blood_requests.selectors.tracking import request_detail
from blood_requests.serializers.tracking import EmptyQuerySerializer
from blood_requests.services.closure import close_request


@method_decorator(csrf_protect, name='dispatch')
class RequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsRequestReader]

    def get(self, request, request_id):
        query = EmptyQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(request_detail(actor=request.user, request_id=request_id))


@method_decorator(csrf_protect, name='dispatch')
class RequestCloseView(APIView):
    permission_classes = [IsAuthenticated, IsRequester]

    def post(self, request, request_id):
        query = EmptyQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            body = request.body
        except RawPostDataException:
            # CSRF middleware may already have consumed a multipart body.
            raise ValidationError({'non_field_errors': ['This action accepts no request body.']}) from None
        if body:
            raise ValidationError({'non_field_errors': ['This action accepts no request body.']})
        return Response(close_request(actor=request.user, request_id=request_id))
