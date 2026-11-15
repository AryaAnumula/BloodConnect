"""BB-19: owning requester closes a fully issued request once, under its row lock.

No inventory access, issue writer, extra schema or notification event. CLOSED replay is
read-only, including updated_at. Both foreign and missing requests use the same lookup.
"""
import uuid

from django.db import DatabaseError, transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from blood_requests.dto import request_dto
from blood_requests.exceptions import CloseInvalidTransition, StorageUnavailable
from blood_requests.models import BloodRequest
from blood_requests.permissions import may_submit_request


def close_request(*, actor, request_id) -> dict:
    if not may_submit_request(user=actor):
        raise PermissionDenied()
    try:
        request_uuid = uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        raise NotFound() from None
    try:
        with transaction.atomic():
            try:
                row = BloodRequest.objects.select_for_update().get(
                    pk=request_uuid, requester_id=actor.pk)
            except BloodRequest.DoesNotExist:
                raise NotFound() from None
            if row.status == BloodRequest.Status.CLOSED:
                return request_dto(row)
            if row.status != BloodRequest.Status.ISSUED or row.fulfilled_quantity != row.quantity:
                raise CloseInvalidTransition()
            row.status = BloodRequest.Status.CLOSED
            row.save(update_fields=['status', 'updated_at'])
            return request_dto(row)
    except DatabaseError:
        raise StorageUnavailable() from None
