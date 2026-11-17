"""Caller-owned allocation; no request, IssueRecord, or transport writes."""
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from core.input_schemas import BLOOD_GROUPS
from inventory.exceptions import InventoryUnavailable, TransactionRequired, UnitConflict, UnsafeUnit
from inventory.models import BloodUnit
from inventory.permissions import require_staff


def allocate_units(*, actor, unit_ids: list, blood_group: str, component_type: str, issued_at) -> list[dict]:
    require_staff(actor)
    if not connection.in_atomic_block:
        raise TransactionRequired('Allocation requires a caller transaction.')
    if (not isinstance(unit_ids, list) or not unit_ids or blood_group not in BLOOD_GROUPS
            or component_type not in BloodUnit.Component.values
            or not isinstance(issued_at, datetime) or timezone.is_naive(issued_at)):
        raise ValidationError({'non_field_errors': ['Invalid allocation input.']})
    try:
        if any(not isinstance(value, (str, UUID)) for value in unit_ids):
            raise ValueError()
        ids = sorted(UUID(str(value)) for value in unit_ids)
    except (ValueError, TypeError, AttributeError):
        raise ValidationError({'unit_ids': ['Valid unique UUIDs are required.']}) from None
    if len(ids) != len(set(ids)):
        raise ValidationError({'unit_ids': ['Valid unique UUIDs are required.']})
    try:
        with transaction.atomic():  # Savepoint only; outer caller retains rollback ownership.
            units = list(BloodUnit.objects.select_for_update().filter(pk__in=ids).order_by('id'))
            if len(units) != len(ids):
                raise NotFound()
            today = timezone.localdate(timezone=ZoneInfo('Asia/Kolkata'))  # AFTER all locks.
            for unit in units:
                if unit.status == 'ISSUED':
                    raise UnitConflict()
                if (unit.status != 'AVAILABLE' or today >= unit.expiry_date
                        or unit.blood_group != blood_group or unit.component_type != component_type):
                    raise UnsafeUnit()
            BloodUnit.objects.filter(pk__in=ids).update(status='ISSUED')
            return [{'unit_id': str(unit.pk), 'quantity': 1} for unit in units]
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
