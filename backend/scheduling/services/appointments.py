"""BB-21 booking. One atomic transaction; lock order camp -> slot -> donor profile -> bookings
(walk-in: slot first).

Reminder creation and cancellation are persisted in the same transaction as the appointment.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from core.errors import DecisionRequired
from donors.eligibility_reader import read_saved_results
from donors.models import DonorProfile
from notification_adapter.services.reminders import schedule_appointment_reminder, cancel_appointment_reminders
from scheduling.dto import appointment_dto
from scheduling.exceptions import (AppointmentNotCancellable, CapacityConflict, DuplicateBooking, IneligibleDonor,
                                   PolicyUnresolved, SlotUnavailable)
from scheduling.models import Appointment, Camp, Slot
from scheduling.permissions import require_camp_role


def _lock_slot(slot_id):
    """Lock the camp (if any), then the slot. Returns (camp_or_None, slot)."""
    try:
        camp_id = Slot.objects.values_list('camp_id', flat=True).get(pk=slot_id)
    except (Slot.DoesNotExist, DjangoValidationError, ValueError):
        raise NotFound() from None
    camp = Camp.objects.select_for_update().get(pk=camp_id) if camp_id else None
    try:
        slot = Slot.objects.select_for_update().get(pk=slot_id)
    except Slot.DoesNotExist:
        raise NotFound() from None
    if slot.camp_id != camp_id:
        raise SlotUnavailable()  # the slot changed while we waited; the caller can retry
    return camp, slot


def _require_current_eligibility(profile) -> None:
    try:
        saved = read_saved_results(donor_ids=[profile.pk]).get(str(profile.pk))
    except DecisionRequired:
        raise PolicyUnresolved('Screening rules are not configured.') from None
    # S2-10 (Arya, 14 Nov): a result is trusted only if it is ELIGIBLE, assessed under the current
    # rules (is_stale) AND not superseded by a later confirmed collection (is_history_stale).
    if (saved is None or saved['status'] != 'ELIGIBLE'
            or saved['is_stale'] or saved['is_history_stale']):
        raise IneligibleDonor()


def book_appointment(*, actor, slot_id, now=None) -> dict:
    require_camp_role(user=actor, action='book')

    with transaction.atomic():
        camp, slot = _lock_slot(slot_id)
        # Agreed lock order: Camp -> Slot -> DonorProfile -> Appointment. The profile is locked and
        # read here, inside the transaction, so a collection confirmed at the same moment (which
        # locks the same row) is either seen by the eligibility check or committed after us.
        try:
            # NO KEY UPDATE (not FOR UPDATE): same mode as donors' screening and
            # record_confirmed_collection, so they serialise against each other, but FK inserts to
            # this profile (FOR KEY SHARE) are not blocked and cannot form a lock-upgrade deadlock.
            profile = DonorProfile.objects.select_for_update(no_key=True).get(user_id=actor.pk)
        except DonorProfile.DoesNotExist:
            raise IneligibleDonor('Complete donor registration and screening before booking.') from None
        if slot.status != Slot.Status.OPEN or (camp is not None and camp.status != Camp.Status.ACTIVE):
            raise SlotUnavailable()
        # Read the clock only now, after every lock is held (Arya, 14 Nov): a request that waited
        # on a lock must not succeed with a timestamp taken before the wait.
        booked_at = now or timezone.now()
        if slot.starts_at <= booked_at:
            raise SlotUnavailable()
        _require_current_eligibility(profile)
        confirmed = Appointment.objects.filter(slot=slot, status=Appointment.Status.CONFIRMED)
        if confirmed.filter(donor=profile).exists():
            raise DuplicateBooking()
        if confirmed.count() >= slot.capacity:
            raise CapacityConflict('This slot is full.')
        if camp is not None:
            camp_total = Appointment.objects.filter(
                slot__camp=camp, status=Appointment.Status.CONFIRMED).count()
            if camp_total >= camp.capacity:
                raise CapacityConflict('This camp is full.')
        try:
            with transaction.atomic():
                appointment = Appointment.objects.create(donor=profile, slot=slot)
        except IntegrityError:
            raise DuplicateBooking() from None
        schedule_appointment_reminder(appointment_id=appointment.pk, donor_user_id=actor.pk,
                                      starts_at=slot.starts_at, booked_at=booked_at)
    appointment.slot = slot
    return appointment_dto(appointment)


def cancel_appointment(*, actor, appointment_id, now=None) -> dict:
    """A donor cancels their OWN confirmed appointment before its slot starts.

    Repeating the call is harmless: an already cancelled appointment is returned unchanged and
    capacity is never released twice (capacity is counted from CONFIRMED rows only). History is
    kept (status CANCELLED + cancelled_at). Someone else's appointment is indistinguishable from
    an unknown id (404). Lock order camp -> slot -> appointment, same as booking.

    Pending reminders are invalidated in the same transaction.
    """
    require_camp_role(user=actor, action='cancel_own')
    try:
        profile = DonorProfile.objects.get(user_id=actor.pk)
        slot_id = Appointment.objects.values_list('slot_id', flat=True).get(
            pk=appointment_id, donor=profile)
    except (DonorProfile.DoesNotExist, Appointment.DoesNotExist, DjangoValidationError, ValueError):
        raise NotFound() from None

    with transaction.atomic():
        _camp, slot = _lock_slot(slot_id)
        try:
            appointment = Appointment.objects.select_for_update().get(pk=appointment_id, donor=profile)
        except Appointment.DoesNotExist:
            raise NotFound() from None
        if appointment.status != Appointment.Status.CANCELLED:
            # Clock read after all locks are held, immediately before the start boundary check.
            current = now or timezone.now()
            if slot.starts_at <= current:
                raise AppointmentNotCancellable()
            appointment.status = Appointment.Status.CANCELLED
            appointment.cancelled_at = current
            appointment.save(update_fields=['status', 'cancelled_at', 'updated_at'])
            cancel_appointment_reminders(appointment_id=appointment.pk)
    appointment.slot = slot
    return appointment_dto(appointment)
