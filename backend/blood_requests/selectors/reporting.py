"""Current submitted count for the dashboard; issue aggregation remains BB16-owned."""
from blood_requests.models import BloodRequest


def pending_request_count() -> int:
    return BloodRequest.objects.filter(status=BloodRequest.Status.SUBMITTED).count()
