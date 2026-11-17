"""Read-only request reporting selectors.

pending_request_count: Arya's BB-23 dashboard count (function kept unchanged from team/arya-bb23).
request_issue_totals: BB-16 issue history for BB-24 reports (contract v1.1 / BC-D047).
"""
from datetime import datetime

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from blood_requests.models import BloodRequest, IssueRecord


def pending_request_count() -> int:
    return BloodRequest.objects.filter(status=BloodRequest.Status.SUBMITTED).count()


def _aware(value) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def request_issue_totals(*, start=None, end=None) -> dict:
    """{"issued_unit_count": int} summed from actual IssueRecord rows; no PII, no status proxies.

    Both None: all history. Otherwise both must be aware datetimes with start < end; the
    half-open interval [start, end) filters issued_at. Invalid bounds raise ValidationError
    (no all-time fallback). Storage errors propagate, so reports show "unavailable", never a
    fabricated 0.
    """
    if (start is None) != (end is None):
        raise ValidationError({'non_field_errors': ['Provide both start and end, or neither.']})
    if start is not None:
        errors = {name: ['Use a timezone-aware date and time.']
                  for name, value in (('start', start), ('end', end)) if not _aware(value)}
        if errors:
            raise ValidationError(errors)
        if not start < end:
            raise ValidationError({'end': ['End must be after start.']})
    rows = IssueRecord.objects.all()
    if start is not None:
        rows = rows.filter(issued_at__gte=start, issued_at__lt=end)
    total = rows.aggregate(total=Sum('issued_quantity'))['total'] or 0
    return {'issued_unit_count': int(total)}
