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
    deadline=starts_at-timedelta(hours=24);late=booked_at>deadline
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
