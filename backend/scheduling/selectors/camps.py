"""BB-20 read-only camp listing. Stable order: starts_at, then id.

A DONOR never sees CANCELLED camps, with or without a status filter (Arya, 14 Nov): the
visibility rule is applied first, so status=CANCELLED gives a donor an empty page with count 0.
STAFF/ADMIN see all and may filter by status.
"""
from scheduling.dto import camp_dto
from scheduling.models import Camp
from scheduling.permissions import require_camp_role


def list_camps(*, actor, filters: dict, page: int = 1, page_size: int = 20) -> dict:
    require_camp_role(user=actor, action='list')
    queryset = Camp.objects.all()
    if getattr(actor, 'role', None) == 'DONOR':
        queryset = queryset.exclude(status=Camp.Status.CANCELLED)
    status = (filters or {}).get('status')
    if status:
        queryset = queryset.filter(status=status)
    count = queryset.count()
    offset = (page - 1) * page_size
    rows = list(queryset.order_by('starts_at', 'id')[offset:offset + page_size])
    return {'count': count, 'page': page, 'page_size': page_size,
            'results': [camp_dto(row) for row in rows]}
