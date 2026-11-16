"""BB-20 camp services. Return JSON-ready DTOs, never ORM instances.

Role checks go through scheduling.permissions (BC-D001: active non-superuser STAFF/ADMIN).
Camp cancellation (BC-D008/D009, S2-05/S2-06) is cancel_camp below; refusing a capacity
reduction below confirmed bookings or a time change that strands slots is _check_bookings.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from core.errors import DecisionRequired
from donors.models import DonorProfile
from notification_adapter.services.reminders import (cancel_appointment_reminders,
                                                     enqueue_camp_cancellation)
from scheduling.dto import camp_dto
from scheduling.exceptions import CapacityConflict, ReminderUnavailable, ScheduleConflict
from scheduling.models import Appointment, Camp, Slot
from scheduling.permissions import require_camp_role

EDITABLE_FIELDS = ('name', 'location', 'starts_at', 'ends_at', 'capacity')


class CampNotEditable(APIException):
    # BC-D003..D007: editing a CANCELLED camp is 422.
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
    """Contract (PATCH /camps), BC-D005/D007: runs under the camp row lock.

    Capacity may not drop below the CONFIRMED appointment count (equality is allowed), and every
    linked slot, whether open, empty, cancelled or historical, must stay inside a moved camp
    interval (409 slot_conflict). Slots are never moved or deleted silently.
    """
    confirmed = Appointment.objects.filter(slot__camp=camp, status=Appointment.Status.CONFIRMED)
    if 'capacity' in changes and changes['capacity'] < confirmed.count():
        raise CapacityConflict('Capacity cannot be below the number of active bookings.')
    if 'starts_at' in changes or 'ends_at' in changes:
        starts = changes.get('starts_at', camp.starts_at)
        ends = changes.get('ends_at', camp.ends_at)
        # BC-D005: EVERY linked slot (open, cancelled or historical, with or without bookings)
        # must stay inside the camp interval. A conflicting change is rejected with 409
        # slot_conflict; slots are never moved or deleted silently.
        linked = Slot.objects.filter(camp=camp)
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


def cancel_camp(*, actor, camp_id, reason, now=None) -> dict:
    """Cancel an ACTIVE camp and every CONFIRMED appointment in it, atomically (S2-05/S2-06).

    One transaction, lock order Camp -> ALL linked slots (UUID order) -> affected appointments
    (UUID order). The donor profile is never locked here (and so never after an appointment
    lock). The cancellation time is read once, after every lock is held, persisted on the camp and
    reused for every appointment and notification intent, so a replay never invents a new time.

    For each newly cancelled appointment: pending/blocked/leased reminders are invalidated and
    exactly ONE durable APPOINTMENT_CANCELLED intent is stored for the donor ACCOUNT id, in this
    same transaction. Any failure (domain write, invalidation, intent persistence) rolls
    back the whole operation. Delivery happens later, after commit, through the existing
    provider; a send already in flight cannot be recalled and mock delivery is not real
    SMS/email. Slots and appointments are kept for history. An already CANCELLED camp is returned
    unchanged (original reason/time) with no new effects.
    """
    require_camp_role(user=actor, action='cancel')
    reason = reason.strip() if isinstance(reason, str) else ''
    if not 1 <= len(reason) <= 240:
        raise ValidationError({'reason': ['Enter a reason of 1 to 240 characters.']})
    with transaction.atomic():
        try:
            camp = Camp.objects.select_for_update().get(pk=camp_id)
        except (Camp.DoesNotExist, DjangoValidationError, ValueError):
            raise NotFound() from None
        if camp.status == Camp.Status.CANCELLED:
            return camp_dto(camp)  # replay: original reason/time kept, no new effects
        list(Slot.objects.select_for_update().filter(camp=camp).order_by('pk').values_list('pk', flat=True))
        affected = list(Appointment.objects.select_for_update()
                        .filter(slot__camp=camp, status=Appointment.Status.CONFIRMED)
                        .order_by('pk').values_list('pk', 'donor_id'))
        # Clock read after all locks are held.
        cancelled_at = now or timezone.now()
        accounts = dict(DonorProfile.objects.filter(pk__in={donor for _, donor in affected})
                        .values_list('pk', 'user_id'))  # plain read: no donor lock
        try:
            camp.status = Camp.Status.CANCELLED
            camp.cancel_reason = reason
            camp.cancelled_at = cancelled_at
            camp.save(update_fields=['status', 'cancel_reason', 'cancelled_at', 'updated_at'])
            for appointment_id, donor_id in affected:
                Appointment.objects.filter(pk=appointment_id).update(
                    status=Appointment.Status.CANCELLED, cancelled_at=cancelled_at,
                    updated_at=cancelled_at)
                cancel_appointment_reminders(appointment_id=appointment_id)
                enqueue_camp_cancellation(appointment_id=appointment_id,
                                          donor_user_id=accounts[donor_id],
                                          cancelled_at=cancelled_at)
        except DecisionRequired:
            raise ReminderUnavailable(
                'Notification delivery is not configured; the camp was not cancelled.') from None
        return camp_dto(camp)
