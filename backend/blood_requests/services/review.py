"""BB-18 public service (BC-D029-b/d/f):
review_request(*, actor, request_id, status, rejection_reason=None) -> dict (BloodRequest DTO).

Only SUBMITTED -> APPROVED or REJECTED, once. Owns the transaction: locks the row with
select_for_update, rereads its state after the lock, then saves status, reason, reviewer and
time together. A concurrent or repeated review gets 422 invalid_transition and never overwrites
the first decision. No stock check/reservation, no fulfilled change, no notification.
"""
import uuid

from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from blood_requests.dto import request_dto
from blood_requests.exceptions import InvalidTransition, StorageUnavailable
from blood_requests.models import BloodRequest
from blood_requests.permissions import may_review_requests
from blood_requests.serializers.review import DECISIONS, REASON_MAX


def _clean_reason(status, rejection_reason):
    if status == 'APPROVED':
        if rejection_reason is not None:
            raise ValidationError({'rejection_reason': ['Leave out the rejection reason when approving.']})
        return None
    if not isinstance(rejection_reason, str) or not rejection_reason.strip():
        raise ValidationError({'rejection_reason': ['A rejection reason is required.']})
    reason = rejection_reason.strip()
    if len(reason) > REASON_MAX:
        raise ValidationError({'rejection_reason': [f'Use at most {REASON_MAX} characters.']})
    return reason


def review_request(*, actor, request_id, status: str, rejection_reason: str | None = None) -> dict:
    if not may_review_requests(user=actor):
        raise PermissionDenied()
    if not isinstance(status, str) or status not in DECISIONS:
        raise ValidationError({'status': ['Select a permitted value.']})
    reason = _clean_reason(status, rejection_reason)
    try:
        request_uuid = uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        raise NotFound() from None
    try:
        with transaction.atomic():
            try:
                row = BloodRequest.objects.select_for_update().get(pk=request_uuid)
            except BloodRequest.DoesNotExist:
                raise NotFound() from None
            if row.status != BloodRequest.Status.SUBMITTED:  # reread after the lock
                raise InvalidTransition()
            row.status = status
            row.rejection_reason = reason
            row.reviewed_by = actor
            row.reviewed_at = timezone.now()
            row.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at',
                                    'updated_at'])
            return request_dto(row)
    except DatabaseError:
        raise StorageUnavailable() from None  # rolled back; no raw database detail
