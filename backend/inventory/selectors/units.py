from zoneinfo import ZoneInfo
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.exceptions import NotFound

from inventory.exceptions import InventoryUnavailable
from inventory.models import BloodUnit
from inventory.permissions import require_staff
from inventory.serializers import UnitQuery
from inventory.services.units import unit_dto


def unit_list(*, actor, filters):
    require_staff(actor)
    query = UnitQuery(data=filters)
    query.is_valid(raise_exception=True)
    values = dict(query.validated_data)
    page, size = values.pop('page'), values.pop('page_size')
    state = values.pop('status', None)
    today = timezone.localdate(timezone=ZoneInfo('Asia/Kolkata'))
    units = BloodUnit.objects.filter(**values)
    if state == 'EXPIRED':
        units = units.filter(status='AVAILABLE', expiry_date__lte=today)
    elif state == 'AVAILABLE':
        units = units.filter(status='AVAILABLE', expiry_date__gt=today)
    elif state:
        units = units.filter(status=state)
    try:
        count = units.count()
        results = [unit_dto(unit, today=today) for unit in units.order_by('unit_code', 'id')[(page-1)*size:page*size]]
        return {'count': count, 'page': page, 'page_size': size, 'results': results}
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc


def unit_detail(*, actor, unit_id):
    require_staff(actor)
    try:
        return unit_dto(BloodUnit.objects.get(pk=unit_id))
    except BloodUnit.DoesNotExist:
        raise NotFound() from None
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
