"""BB-18 public read boundary (BC-D029-a/f): staff_queue(*, actor, status, page, page_size).

Read-only. Filters, then orders in the database by urgency rank (CRITICAL, URGENT, ROUTINE),
created_at ascending, id ascending, then counts and slices. A page beyond the last one is an
empty result with the truthful filtered count. Returns a RequestPage dict.
"""
from django.db.models import Case, IntegerField, Value, When
from rest_framework.exceptions import PermissionDenied, ValidationError

from blood_requests.dto import request_dto
from blood_requests.models import BloodRequest
from blood_requests.models.request import STATUS_VALUES, URGENCY_VALUES
from blood_requests.permissions import may_review_requests

URGENCY_RANK = Case(*[When(urgency_level=value, then=Value(rank))
                      for rank, value in enumerate(URGENCY_VALUES)],
                    output_field=IntegerField())


def _whole(value, *, minimum, maximum=None) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return False
    return maximum is None or value <= maximum


def staff_queue(*, actor, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    if not may_review_requests(user=actor):
        raise PermissionDenied()
    if status is None:
        status = BloodRequest.Status.SUBMITTED
    errors = {}
    if not isinstance(status, str) or status not in STATUS_VALUES:
        errors['status'] = ['Select a permitted value.']
    if not _whole(page, minimum=1):
        errors['page'] = ['Enter a whole number of at least 1.']
    if not _whole(page_size, minimum=1, maximum=100):
        errors['page_size'] = ['Enter a whole number from 1 to 100.']
    if errors:
        raise ValidationError(errors)
    rows = (BloodRequest.objects.filter(status=status)
            .annotate(urgency_rank=URGENCY_RANK)
            .order_by('urgency_rank', 'created_at', 'id'))
    count = rows.count()
    start = (page - 1) * page_size
    results = [request_dto(row) for row in rows[start:start + page_size]] if start < count else []
    return {'count': count, 'page': page, 'page_size': page_size, 'results': results}
