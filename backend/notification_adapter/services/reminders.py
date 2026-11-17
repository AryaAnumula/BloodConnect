"""Reminder scheduling boundary for Ankitha's appointment transaction. No fake appointments."""
import uuid
from datetime import timedelta
from django.db import connection
from notification_adapter.models import OutboxIntent
from notification_adapter.policy import require_policy
from .intents import enqueue_intent, _aware, _uuid, EventConflict

def schedule_appointment_reminder(*, appointment_id, donor_user_id, starts_at, booked_at, channels=None) -> dict:
    require_policy('S2-06','S2-07')
    if not connection.in_atomic_block: raise RuntimeError('Caller must own appointment atomic transaction.')
    appointment_id=_uuid(appointment_id);donor_user_id=_uuid(donor_user_id)
    starts_at=_aware(starts_at);booked_at=_aware(booked_at)
    if starts_at<=booked_at: raise ValueError('Appointment must be in the future.')
    deadline=starts_at-timedelta(hours=25);late=booked_at>deadline
    due_at=booked_at if late else deadline
    event_id=uuid.uuid5(uuid.NAMESPACE_URL, f'bloodconnect:reminder:{appointment_id}:{starts_at.isoformat()}')
    result=enqueue_intent(event_id=event_id,recipient_id=donor_user_id,event_type='APPOINTMENT_REMINDER',record_id=appointment_id,due_at=due_at,channels=channels if channels is not None else ['IN_APP'])
    row=OutboxIntent.objects.get(pk=result['id'])
    if row.state=='CANCELLED': raise EventConflict('Cancelled reminder cannot be silently reactivated.')
    if row.scheduled_for is not None and row.scheduled_for!=starts_at: raise EventConflict('Reminder source changed.')
    if row.scheduled_for is None:
        row.scheduled_for=starts_at;row.late_booking=late;row.save(update_fields=['scheduled_for','late_booking'])
    return {**result,'due_at':due_at.isoformat(),'late_booking':late}

def cancel_appointment_reminders(*, appointment_id) -> int:
    require_policy('S2-06','S2-07')
    if not connection.in_atomic_block: raise RuntimeError('Caller must own cancellation atomic transaction.')
    return OutboxIntent.objects.filter(record_id=_uuid(appointment_id),event_type='APPOINTMENT_REMINDER',state__in=['PENDING','BLOCKED','LEASED']).update(state='CANCELLED',lease_token=None,lease_until=None,last_error_code='appointment_cancelled')


def reminder_state(*, appointment_id):
    """Read the latest real reminder state, or raise LookupError if absent.

    Internal trusted service: callers must enforce appointment ownership.
    """
    require_policy('S2-06', 'S2-07')
    row = OutboxIntent.objects.filter(record_id=_uuid(appointment_id), event_type='APPOINTMENT_REMINDER').order_by('-created_at', '-id').first()
    if row is None:
        raise LookupError('Reminder intent is unavailable.')
    return row.state


def public_reminder_state(*, appointment_id):
    """Appointment DTO projection: a real queued/blocked/leased intent is still pending.

    Never invent a pending intent when none exists. Internal dispatch diagnostics retain
    the raw BLOCKED/LEASED states; this maps to the existing four-value public contract.
    """
    state = reminder_state(appointment_id=appointment_id)
    if state in {'PENDING', 'BLOCKED', 'LEASED'}:
        return 'PENDING'
    if state in {'DELIVERED', 'FAILED', 'CANCELLED'}:
        return state
    raise LookupError('Reminder state is unavailable.')


def enqueue_camp_cancellation(*, appointment_id, donor_user_id, cancelled_at, channels=None):
    """Persist one cancellation event in the caller's atomic transaction."""
    appointment_id = _uuid(appointment_id)
    event_id = uuid.uuid5(uuid.NAMESPACE_URL, f'bloodconnect:camp-cancel:{appointment_id}')
    return enqueue_intent(event_id=event_id, recipient_id=donor_user_id,
                          event_type='APPOINTMENT_CANCELLED', record_id=appointment_id,
                          due_at=cancelled_at, channels=channels if channels is not None else ['IN_APP'])
