"""BB-21 slot listing. Stable order: starts_at, then id. A DONOR sees only OPEN slots of ACTIVE
camps (or walk-ins); STAFF/ADMIN see all."""
from django.db.models import Count, Q

from scheduling.dto import slot_dto
from scheduling.models import Appointment, Camp, Slot
from scheduling.permissions import require_camp_role


def list_slots(*, actor, filters: dict, page: int = 1, page_size: int = 20) -> dict:
    require_camp_role(user=actor, action='slot_list')
    filters = filters or {}
    queryset = Slot.objects.annotate(confirmed=Count(
        'appointments', filter=Q(appointments__status=Appointment.Status.CONFIRMED)))
    if getattr(actor, 'role', None) == 'DONOR':
        queryset = queryset.filter(status=Slot.Status.OPEN).exclude(camp__status=Camp.Status.CANCELLED)
    if filters.get('camp_id') is not None:
        queryset = queryset.filter(camp_id=filters['camp_id'])
    if filters.get('kind') == 'CAMP':
        queryset = queryset.filter(camp__isnull=False)
    elif filters.get('kind') == 'WALK_IN':
        queryset = queryset.filter(camp__isnull=True)
    if filters.get('from') is not None:
        queryset = queryset.filter(starts_at__gte=filters['from'])
    if filters.get('to') is not None:
        queryset = queryset.filter(starts_at__lte=filters['to'])
    count = queryset.count()
    offset = (page - 1) * page_size
    rows = list(queryset.order_by('starts_at', 'id')[offset:offset + page_size])
    return {'count': count, 'page': page, 'page_size': page_size,
            'results': [slot_dto(row, row.confirmed) for row in rows]}
