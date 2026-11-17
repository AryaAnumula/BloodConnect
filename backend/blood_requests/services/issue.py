"""BB-16 public service (docs/sprint2/services.md, BC-D026):
issue_request(*, actor, request_id, unit_ids) -> dict (IssueResponse).

One caller-owned transaction, all or nothing:
  1. lock the BloodRequest (FOR NO KEY UPDATE) and recheck it is APPROVED;
  2. reject a batch larger than quantity - fulfilled_quantity (422 oversupply);
  3. call inventory allocate_units (locks units in UUID order, rechecks usability, marks ISSUED);
  4. verify the returned DTOs exactly match the selected units;
  5. write one issue record per unit, then fulfilled_quantity += n and APPROVED -> ISSUED when
     exactly fulfilled (a partial batch stays APPROVED).
No network call and no independent commit inside the transaction. No notification.

Provider: Yashwitha's inventory.services.allocation.allocate_units (contract v1.1), imported
at call time; if the inventory module is absent the service fails closed with 503
inventory_unavailable before writing anything. IssueRecord (OneToOne PROTECT unit FK)
is the durable issue history.
"""
import uuid

from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from blood_requests.exceptions import (IssueInvalidTransition, Oversupply,
                                       StorageUnavailable, UnitConflict)
from blood_requests.integrations.inventory import (checked_allocation, load_allocate_units,
                                                   translate_provider_error)
from blood_requests.models import BloodRequest, IssueRecord
from blood_requests.permissions import may_issue_requests
from blood_requests.serializers.issue import clean_unit_ids


def _write_issue_records(*, blood_request, unit_ids, actor, issued_at) -> list[dict]:
    """One protected, unique issue record per unit (issued_quantity fixed at 1)."""
    records = [IssueRecord.objects.create(request=blood_request, unit_id=unit_id, issued_by=actor,
                                          issued_at=issued_at, issued_quantity=1)
               for unit_id in unit_ids]
    return [{'id': str(r.id), 'request_id': str(r.request_id), 'unit_id': str(r.unit_id),
             'issued_by': str(r.issued_by_id), 'issued_at': r.issued_at.isoformat(),
             'issued_quantity': r.issued_quantity} for r in records]


def issue_request(*, actor, request_id, unit_ids) -> dict:
    if not may_issue_requests(user=actor):
        raise PermissionDenied()
    selected = clean_unit_ids(unit_ids)  # 400 on bad/duplicate ids; sorted canonical
    try:
        request_uuid = uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        raise NotFound() from None
    allocate_units = load_allocate_units()  # 503 while the provider is missing
    try:
        with transaction.atomic():
            try:
                row = BloodRequest.objects.select_for_update(no_key=True).get(pk=request_uuid)
            except BloodRequest.DoesNotExist:
                raise NotFound() from None
            if row.status != BloodRequest.Status.APPROVED:  # rechecked after the lock
                raise IssueInvalidTransition()
            if len(selected) > row.quantity - row.fulfilled_quantity:
                raise Oversupply()
            issued_at = timezone.now()  # after the request lock; provider refreshes after unit locks
            try:
                result = allocate_units(actor=actor, unit_ids=list(selected), blood_group=row.blood_group,
                                        component_type=row.component_type, issued_at=issued_at)
            except Exception as exc:
                mapped = translate_provider_error(exc)
                if mapped is None:
                    raise
                raise mapped from None
            allocated = checked_allocation(result, selected)
            issues = _write_issue_records(blood_request=row, unit_ids=allocated, actor=actor,
                                          issued_at=issued_at)
            row.fulfilled_quantity += len(allocated)
            if row.fulfilled_quantity == row.quantity:
                row.status = BloodRequest.Status.ISSUED
            row.save(update_fields=['fulfilled_quantity', 'status', 'updated_at'])
            return {'issues': issues, 'fulfilled_quantity': row.fulfilled_quantity,
                    'request_status': row.status}
    except IntegrityError:
        raise UnitConflict() from None  # unique unit issue record: replay/concurrent issue
    except DatabaseError:
        raise StorageUnavailable() from None
