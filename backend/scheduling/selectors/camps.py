"""BB-20 read-only camp listing. Stable order: starts_at, then id.

Default list (no status filter): a DONOR does not see CANCELLED camps; STAFF/ADMIN see all.
PENDING DECISION (Arya, 12 Nov): this is a default-list rule only. An explicit status filter is
applied as given for every allowed role, so a DONOR who passes status=CANCELLED still gets
cancelled camps. Whether donors may explicitly request them is not decided.
"""
from scheduling.dto import camp_dto
from scheduling.models import Camp
from scheduling.permissions import require_camp_role


def list_camps(*, actor, filters: dict, page: int = 1, page_size: int = 20) -> dict:
    require_camp_role(user=actor, action='list')
    queryset = Camp.objects.all()
    status = (filters or {}).get('status')
    if status:
        queryset = queryset.filter(status=status)
    elif getattr(actor, 'role', None) == 'DONOR':
        queryset = queryset.exclude(status=Camp.Status.CANCELLED)
    count = queryset.count()
    offset = (page - 1) * page_size
    rows = list(queryset.order_by('starts_at', 'id')[offset:offset + page_size])
    return {'count': count, 'page': page, 'page_size': page_size,
            'results': [camp_dto(row) for row in rows]}
