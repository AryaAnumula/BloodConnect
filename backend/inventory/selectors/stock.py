
"""Read-only stock aggregation helpers."""

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime

from inventory.services.policy import (
    SUPPORTED_COMPONENTS,
    is_unit_usable,
)


STORED_STATUSES = frozenset({
    "AVAILABLE",
    "ISSUED",
    "DISCARDED",
    "QUARANTINED",
})


def summarize_usable_stock(
    *,
    units: Iterable[Mapping[str, object]],
    today: date,
) -> list[dict[str, object]]:
    """Count usable units by blood group and component."""
    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("Today must be a date.")

    counts: Counter[tuple[str, str]] = Counter()

    for unit in units:
        if not isinstance(unit, Mapping):
            raise ValueError("Each unit must be a mapping.")

        blood_group = unit.get("blood_group")
        component_type = unit.get("component_type")
        status = unit.get("status")
        expiry_date = unit.get("expiry_date")
        quantity = unit.get("quantity")

        if not isinstance(blood_group, str) or not blood_group.strip():
            raise ValueError("Each unit must have a valid blood group.")

        if (
            not isinstance(component_type, str)
            or component_type not in SUPPORTED_COMPONENTS
        ):
            raise ValueError("Each unit must have a supported component.")

        if (
            not isinstance(status, str)
            or status not in STORED_STATUSES
        ):
            raise ValueError("Each unit must have a valid stored status.")

        if (
            not isinstance(expiry_date, date)
            or isinstance(expiry_date, datetime)
        ):
            raise ValueError("Each unit must have a valid expiry date.")

        if type(quantity) is not int or quantity != 1:
            raise ValueError("Each blood unit must have quantity exactly 1.")

        if is_unit_usable(
            status=status,
            expiry_date=expiry_date,
            today=today,
        ):
            counts[(blood_group, component_type)] += 1

    return [
        {
            "blood_group": blood_group,
            "component_type": component_type,
            "available_units": count,
        }
        for (blood_group, component_type), count in sorted(counts.items())
    ]


def usable_units(*, today):
    """Single ORM inclusion rule shared by stock and alert evaluation."""
    from inventory.models import BloodUnit
    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError('A local date is required.')
    return BloodUnit.objects.filter(status='AVAILABLE', expiry_date__gt=today)


def stock_summary(*, actor, filters: dict, page=1, page_size=20) -> dict:
    from zoneinfo import ZoneInfo
    from django.db import DatabaseError
    from django.db.models import Count
    from django.utils import timezone
    from rest_framework.exceptions import ValidationError
    from inventory.exceptions import InventoryUnavailable
    from inventory.models import BloodUnit
    from inventory.permissions import require_stock_reader
    from inventory.serializers import StockQuery

    require_stock_reader(actor)
    if (not isinstance(filters, dict) or set(filters) - {'blood_group', 'component_type'}
            or type(page) is not int or type(page_size) is not int):
        raise ValidationError({'non_field_errors': ['Invalid stock query.']})
    query = StockQuery(data=filters | {'page': page, 'page_size': page_size})
    query.is_valid(raise_exception=True)
    values = dict(query.validated_data)
    page, size = values.pop('page'), values.pop('page_size')
    today = timezone.localdate(timezone=ZoneInfo('Asia/Kolkata'))
    try:
        rows = list(usable_units(today=today).filter(**values).values('blood_group', 'component_type').annotate(
                available_quantity=Count('id')).order_by('blood_group', 'component_type'))
        return {'count': len(rows), 'page': page, 'page_size': size,
                'results': rows[(page-1)*size:page*size]}
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
