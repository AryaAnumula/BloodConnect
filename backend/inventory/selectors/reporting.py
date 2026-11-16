from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import DatabaseError
from django.utils import timezone

from inventory.exceptions import InventoryUnavailable
from inventory.models import BloodUnit, CollectionEvent, InventoryDisposition

KOLKATA = ZoneInfo('Asia/Kolkata')


def collection_wastage_totals(*, start, end) -> dict:
    if (not isinstance(start, datetime) or not isinstance(end, datetime)
            or timezone.is_naive(start) or timezone.is_naive(end) or start >= end):
        raise ValueError('Aware increasing bounds are required.')
    # DateFields represent local midnight. Use ceiling dates for general half-open bounds.
    local_start, local_end = start.astimezone(KOLKATA), end.astimezone(KOLKATA)
    first = local_start.date() + timedelta(days=local_start.time() != time.min)
    stop = local_end.date() + timedelta(days=local_end.time() != time.min)
    try:
        return {
            'donation_event_count': CollectionEvent.objects.filter(status='CONFIRMED',
                collection_date__gte=first, collection_date__lt=stop).count(),
            'collected_unit_count': BloodUnit.objects.filter(collection_event__status='CONFIRMED',
                collection_date__gte=first, collection_date__lt=stop).count(),
            'wasted_unit_count': InventoryDisposition.objects.filter(to_status='DISCARDED',
                occurred_at__gte=start, occurred_at__lt=end).count(),
        }
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
