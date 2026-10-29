"""BB-07, Ankitha. POST /api/v1/donors/{donor_id}/eligibility.

donor_id is the donor PROFILE UUID, not the account UUID.
Demonstration rules only; this is NOT a statement that anyone is medically fit to donate.
"""
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.health_access import record_donor_health_denial
from accounts.permissions import IsDonorOrAuthorizedStaff
from core.errors import DecisionRequired
from core.input_schemas import ScreeningInputSerializer
from core.parsers import StrictJSONParser
from core.stubs import AuthenticatedPostStub
from donors.configuration import approved_screening_rules
from donors.services.screening import ScreeningAccessDenied, is_stale, screen_donor


def _error(request, status, code, message):
    request_id = getattr(request, 'request_id', '')
    return Response(
        {'error': {'code': code, 'message': message, 'fields': {}, 'request_id': request_id}},
        status=status)


def result_payload(result, rules):
    """Exact EligibilityResult contract shape; no health answers are echoed back."""
    return {
        'id': str(result.id),
        'donor_id': str(result.donor_id),
        'status': result.status,
        'reason_codes': list(result.reason_codes),
        'reasons': list(result.reasons),
        'assessed_at': result.assessed_at.isoformat(),
        'rules_version': result.rules_version,
        'is_stale': is_stale(result, rules),
    }


class ScreeningView(AuthenticatedPostStub):
    # AuthenticatedPostStub applies csrf_protect. The role gate rejects ADMIN, REQUESTER, plain
    # STAFF and superusers (403 forbidden) before any record lookup; the object check in
    # screen_donor (may_view_donor_health) then proves ownership or clinical authorization.
    parser_classes = [StrictJSONParser]
    permission_classes = [IsAuthenticated, IsDonorOrAuthorizedStaff]

    def post(self, request, donor_id, *args, **kwargs):
        serializer = ScreeningInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 validation_error via core.errors
        try:
            rules = approved_screening_rules()
            result = screen_donor(actor=request.user, donor_id=donor_id,
                                  answers=serializer.validated_data)
        except DecisionRequired:
            return _error(request, 409, 'policy_unresolved',
                          'Screening rules are not available. Please try again later.')
        except ScreeningAccessDenied:
            # Not-yours is a 404 (same as the BB-12 profile endpoint); record exactly one event.
            record_donor_health_denial(request=request)
            raise NotFound() from None
        return Response(result_payload(result, rules))