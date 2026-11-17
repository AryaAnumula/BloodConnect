"""BB-19 owner-first reads. None status means all OWN requests, not the staff default."""
import uuid

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from blood_requests.dto import request_dto
from blood_requests.models import BloodRequest
from blood_requests.models.request import STATUS_VALUES
from blood_requests.permissions import may_review_requests, may_submit_request
from blood_requests.selectors.review_queue import URGENCY_RANK


def own_requests(*, actor, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    if not may_submit_request(user=actor):
        raise PermissionDenied()
    errors = {}
    if status is not None and (not isinstance(status, str) or status not in STATUS_VALUES):
        errors['status'] = ['Select a permitted value.']
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        errors['page'] = ['Enter a whole number of at least 1.']
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
        errors['page_size'] = ['Enter a whole number from 1 to 100.']
    if errors:
        raise ValidationError(errors)
    rows = BloodRequest.objects.filter(requester_id=actor.pk)
    if status is not None:
        rows = rows.filter(status=status)
    rows = rows.annotate(urgency_rank=URGENCY_RANK).order_by('urgency_rank', 'created_at', 'id')
    count = rows.count()
    start = (page - 1) * page_size
    results = [request_dto(row) for row in rows[start:start + page_size]] if start < count else []
    return {'count': count, 'page': page, 'page_size': page_size, 'results': results}


def request_detail(*, actor, request_id) -> dict:
    requester = may_submit_request(user=actor)
    if not requester and not may_review_requests(user=actor):
        raise PermissionDenied()
    try:
        request_uuid = uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        raise NotFound() from None
    rows = BloodRequest.objects.all()
    if requester:
        rows = rows.filter(requester_id=actor.pk)
    try:
        return request_dto(rows.get(pk=request_uuid))
    except BloodRequest.DoesNotExist:
        raise NotFound() from None
