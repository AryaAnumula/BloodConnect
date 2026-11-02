"""Short lease transaction → HTTP outside transaction → compare-and-set completion.

No fake provider success. Missing appointment selector blocks reminders, not general mock alerts.
"""
import importlib,uuid
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from notification_adapter.models import OutboxIntent,DeliveryAttempt
from notification_adapter.client import send_notification_intent,NotificationTransportUnavailable
from notification_adapter.policy import require_policy
from .intents import _aware

class ReminderProviderUnavailable(Exception): pass

def _reminder_current(row):
    if row.scheduled_for is None: raise ReminderProviderUnavailable()
    try:
        reader=getattr(importlib.import_module('scheduling.selectors.reminders'),'reminder_context')
        context=reader(appointment_id=row.record_id)
    except Exception:
        # Fail closed; sanitized code retained. Missing/failed provider is not fake cancellation or delivery.
        raise ReminderProviderUnavailable() from None
    if not isinstance(context,dict): raise ReminderProviderUnavailable()
    try:
        if uuid.UUID(str(context['appointment_id']))!=row.record_id or uuid.UUID(str(context['donor_user_id']))!=row.recipient_id: raise ReminderProviderUnavailable()
        starts=_aware(context['starts_at'])
        status=context['appointment_status'];camp=context['camp_status']
        if status not in {'CONFIRMED','CANCELLED'} or camp not in {None,'ACTIVE','CANCELLED'}: raise ReminderProviderUnavailable()
        return status=='CONFIRMED' and camp in {None,'ACTIVE'} and starts==row.scheduled_for
    except (KeyError,ValueError,TypeError): raise ReminderProviderUnavailable() from None

def dispatch_due(*, now, limit: int=100) -> dict:
    require_policy('S2-06');now=_aware(now)
    if transaction.get_connection().in_atomic_block: raise RuntimeError('Dispatch must run outside caller atomic transaction.')
    if type(limit) is not int or not 1<=limit<=1000: raise ValueError('limit must be1..1000.')
    counts={'delivered':0,'retry':0,'failed':0,'blocked':0,'cancelled':0,'superseded':0}
    candidate=Q(state__in=['PENDING','BLOCKED'],next_attempt_at__lte=now)|Q(state='LEASED',lease_until__lte=now)
    ids=list(OutboxIntent.objects.filter(candidate,due_at__lte=now).order_by('due_at','id').values_list('pk',flat=True)[:limit])
    for pk in ids:
        token=uuid.uuid4()
        with transaction.atomic():
            row=OutboxIntent.objects.select_for_update().filter(pk=pk).first()
            if row is None or row.due_at>now: continue
            # Claim time must be read after acquiring the lock, not at batch start.
            claim_now = _aware(timezone.now())
            eligible=row.state in {'PENDING','BLOCKED'} and row.next_attempt_at<=claim_now or row.state=='LEASED' and row.lease_until is not None and row.lease_until<=claim_now
            if not eligible: continue
            row.state='LEASED';row.lease_token=token;row.lease_until=claim_now+timedelta(seconds=30)
            row.save(update_fields=['state','lease_token','lease_until'])
        target=OutboxIntent.objects.filter(pk=pk,state='LEASED',lease_token=token)
        if row.event_type=='APPOINTMENT_REMINDER':
            try:
                require_policy('S2-07')
                current=_reminder_current(row)
            except Exception:
                target.update(state='BLOCKED',last_error_code='reminder_provider_or_policy_unavailable',next_attempt_at=_aware(timezone.now())+timedelta(seconds=60),lease_token=None,lease_until=None)
                counts['blocked']+=1;continue
            if not current:
                target.update(state='CANCELLED',last_error_code='appointment_changed_or_cancelled',lease_token=None,lease_until=None)
                counts['cancelled']+=1;continue
        # Recheck explicit cancellation after provider read, before HTTP. A race during HTTP cannot unsend a receipt.
        if not target.exists(): counts['superseded']+=1;continue
        event={'event_id':str(row.event_id),'recipient_id':str(row.recipient_id),'type':row.event_type,'record_id':str(row.record_id),'due_at':row.due_at.isoformat(),'channels':row.channels}
        try:
            send_notification_intent(event=event);outcome='DELIVERED';code=''
        except NotificationTransportUnavailable:
            outcome='FAILED';code='transport_unavailable'
        except Exception:
            outcome='FAILED';code='unexpected_transport_failure'
        completed=timezone.now()
        with transaction.atomic():
            locked=OutboxIntent.objects.select_for_update().get(pk=pk)
            if locked.state!='LEASED' or locked.lease_token!=token:
                counts['superseded']+=1;continue
            locked.attempts+=1;locked.lease_token=None;locked.lease_until=None;locked.last_error_code=code
            # The mock service acknowledges all requested channels together. Persist one
            # row per channel; an unacknowledged transport failure proves no receipt.
            for channel in locked.channels:
                receipt_key=f'{locked.event_id}:{channel}' if outcome=='DELIVERED' else None
                DeliveryAttempt.objects.create(intent=locked,channel=channel,receipt_key=receipt_key,attempted_at=completed,outcome=outcome,error_code=code)
            if outcome=='DELIVERED':
                locked.state='DELIVERED';locked.delivered_at=completed
                if locked.scheduled_for is not None:locked.timing_met=not locked.late_booking and completed<=locked.scheduled_for-timedelta(hours=24)
                counts['delivered']+=1
            elif locked.attempts>=3:locked.state='FAILED';counts['failed']+=1
            else:
                locked.state='PENDING';locked.next_attempt_at=completed+timedelta(seconds=60*2**(locked.attempts-1));counts['retry']+=1
            locked.save()
    return counts
