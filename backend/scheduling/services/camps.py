"""BB-20 camp services. Return JSON-ready DTOs, never ORM instances.

Role checks go through scheduling.permissions (PENDING S2-04).
Not implemented yet and waiting on approvals / BB-21:
  - cancel_camp (S2-05 / S2-06: cancels appointments and creates notification intents)
  - refusing a capacity reduction below active bookings, or a time change that strands
    slots: done in _check_bookings (BB-21 models)
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from scheduling.dto import camp_dto
from scheduling.exceptions import CapacityConflict, ScheduleConflict
from scheduling.models import Appointment, Camp, Slot
from scheduling.permissions import require_camp_role

EDITABLE_FIELDS = ('name', 'location', 'starts_at', 'ends_at', 'capacity')


class CampNotEditable(APIException):
    # ASSUMPTION to confirm with Arya: a cancelled camp cannot be edited.
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'A cancelled camp cannot be changed.'


def _check_interval(starts_at, ends_at) -> None:
    if starts_at >= ends_at:
        raise ValidationError({'ends_at': ['End must be after start.']})


def create_camp(*, actor, data: dict) -> dict:
    """Create an ACTIVE camp from already shape-validated data."""
    require_camp_role(user=actor, action='create')
    _check_interval(data['starts_at'], data['ends_at'])
    # Arya (Nov 11): reject NEW camps that start in the past (edits: see update_camp).
    if data['starts_at'] <= timezone.now():
        raise ValidationError({'starts_at': ['A new camp must start in the future.']})
    with transaction.atomic():
        camp = Camp.objects.create(
            name=data['name'], location=data['location'],
            starts_at=data['starts_at'], ends_at=data['ends_at'],
            capacity=data['capacity'])
    return camp_dto(camp)


def _check_bookings(camp, changes) -> None:
    """Contract (PATCH /camps): do not cut capacity below active bookings or strand appointments.

    Runs under the camp row lock. Only slots that have CONFIRMED bookings block a time change;
    empty slots outside the new times are not checked here (open question for Arya).
    """
    confirmed = Appointment.objects.filter(slot__camp=camp, status=Appointment.Status.CONFIRMED)
    if 'capacity' in changes and changes['capacity'] < confirmed.count():
        raise CapacityConflict('Capacity cannot be below the number of active bookings.')
    if 'starts_at' in changes or 'ends_at' in changes:
        starts = changes.get('starts_at', camp.starts_at)
        ends = changes.get('ends_at', camp.ends_at)
        # Arya (14 Nov): every linked slot must stay inside the camp interval, empty ones too.
        # Conflicting changes are rejected; slots are never moved silently. CANCELLED slots are
        # inert history and are not counted (ASSUMPTION, flagged to Arya).
        linked = Slot.objects.filter(camp=camp).exclude(status=Slot.Status.CANCELLED)
        if linked.filter(starts_at__lt=starts).exists() or linked.filter(ends_at__gt=ends).exists():
            raise ScheduleConflict()


def update_camp(*, actor, camp_id, data: dict) -> dict:
    """Apply a partial update under a row lock."""
    require_camp_role(user=actor, action='update')
    changes = {name: data[name] for name in EDITABLE_FIELDS if name in data}
    if not changes:
        raise ValidationError({'non_field_errors': ['Provide at least one field to change.']})
    with transaction.atomic():
        try:
            camp = Camp.objects.select_for_update().get(pk=camp_id)
        except (Camp.DoesNotExist, DjangoValidationError, ValueError):
            raise NotFound() from None
        if camp.status != Camp.Status.ACTIVE:
            raise CampNotEditable()
        # Arya (14 Nov): moving the start to a past time, or exactly now, is rejected. An unchanged
        # start (even if already past) never blocks other edits.
        new_start = changes.get('starts_at')
        if new_start is not None and new_start != camp.starts_at and new_start <= timezone.now():
            raise ValidationError({'starts_at': ['A camp cannot be moved to start in the past.']})
        _check_interval(changes.get('starts_at', camp.starts_at),
                        changes.get('ends_at', camp.ends_at))
        _check_bookings(camp, changes)
        for field, value in changes.items():
            setattr(camp, field, value)
        camp.save(update_fields=[*changes, 'updated_at'])
    return camp_dto(camp)
