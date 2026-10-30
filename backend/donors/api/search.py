"""BB09 actual staff gate + query validation. Screening-reader integration may still block success."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsAuthorizedStaff
from core.errors import DecisionRequired, envelope
from core.input_schemas import SearchInputSerializer
from donors.selectors.search import search_donors


class DonorSearchView(APIView):
    permission_classes = [IsAuthenticated, IsAuthorizedStaff]

    def get(self, request):
        serializer = SearchInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(search_donors(actor=request.user, **serializer.validated_data))
        except DecisionRequired:
            return Response(envelope(request, 'policy_unresolved', 'Screening policy or saved-result integration needs confirmation.'), status=409)
