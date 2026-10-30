"""BB08 authorized saved result response. No medical rules or fixture successes."""
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.health_access import record_donor_health_denial
from accounts.permissions import IsDonorOrAuthorizedStaff
from core.errors import DecisionRequired, envelope
from donors.selectors.results import latest_eligibility_result, ResultAccessDenied


class SavedResultResponse(serializers.Serializer):
    id = serializers.UUIDField()
    donor_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['ELIGIBLE', 'INELIGIBLE'])
    reason_codes = serializers.ListField(child=serializers.CharField())
    reasons = serializers.ListField(child=serializers.CharField())
    assessed_at = serializers.DateTimeField()
    rules_version = serializers.CharField()
    is_stale = serializers.BooleanField()


class EligibilityResultView(APIView):
    permission_classes = [IsAuthenticated, IsDonorOrAuthorizedStaff]

    def get(self, request, donor_id):
        try:
            result = latest_eligibility_result(actor=request.user, donor_id=donor_id)
        except ResultAccessDenied:
            record_donor_health_denial(request=request)
            raise NotFound() from None
        except DecisionRequired:
            return Response(envelope(request, 'policy_unresolved', 'Screening policy or saved-result integration needs confirmation.'), status=409)
        return Response(SavedResultResponse(result).data)
