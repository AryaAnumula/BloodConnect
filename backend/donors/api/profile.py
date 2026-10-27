"""BB-12, Arnav. GET /api/v1/donors/{donor_id}: own donor or authorized clinical staff."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.health_access import record_donor_health_denial
from accounts.permissions import IsDonorOrAuthorizedStaff
from donors.selectors.profile import ProfileAccessDenied, donor_profile_for_actor


@method_decorator(csrf_protect, name='dispatch')
class DonorProfileView(APIView):
    # Anonymous: 403 authentication_required. ADMIN/REQUESTER/plain STAFF: 403 forbidden.
    # Both are logged once by the shared exception hook, before any record lookup.
    permission_classes = [IsAuthenticated, IsDonorOrAuthorizedStaff]

    def get(self, request, donor_id, *args, **kwargs):
        try:
            data = donor_profile_for_actor(actor=request.user, donor_id=donor_id)
        except ProfileAccessDenied:
            # Not-yours is a 404, which the shared hook does not log. Record exactly once here.
            record_donor_health_denial(request=request)
            raise NotFound() from None
        return Response(data)  # A plainly missing profile raises NotFound: no event.