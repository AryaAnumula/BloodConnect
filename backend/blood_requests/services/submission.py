"""BB-17 public service (docs/sprint2/services.md): submit_request(*, actor, data) -> dict.

Approved rules BC-D017–BC-D022: requester is the actor only; server sets SUBMITTED,
fulfilled_quantity 0 and rejection_reason null; no current-stock requirement. The insert
and the returned DTO happen in one atomic block, so a failure leaves no partial row.
INTEGRATION_PENDING: no notification intent is written (notification policy unresolved,
provider not on main).
Exceptions: rest_framework PermissionDenied, ValidationError; core.errors DecisionRequired.
"""
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from blood_requests.configuration import approved_request_policy
from blood_requests.dto import request_dto
from blood_requests.models import BloodRequest
from blood_requests.permissions import may_submit_request
from blood_requests.serializers import RequestCreateSerializer


def submit_request(*, actor, data: dict) -> dict:
    if not may_submit_request(user=actor):
        raise PermissionDenied()
    policy = approved_request_policy()  # DecisionRequired if missing/invalid
    serializer = RequestCreateSerializer(data=data, policy=policy)
    serializer.is_valid(raise_exception=True)
    fields = serializer.validated_data
    with transaction.atomic():
        blood_request = BloodRequest.objects.create(
            requester=actor,
            blood_group=fields['blood_group'],
            component_type=fields['component_type'],
            quantity=fields['quantity'],
            urgency_level=fields['urgency_level'],
            status=BloodRequest.Status.SUBMITTED,
            fulfilled_quantity=0,
            rejection_reason=None,
        )
        return request_dto(blood_request)
