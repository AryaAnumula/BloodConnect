"""Public durable provider. CALL INSIDE THE CALLER'S transaction.atomic(). No network."""
import hashlib,json,uuid
from datetime import datetime, timezone as dt_timezone
from django.db import connection, transaction, IntegrityError
from django.utils import timezone
from notification_adapter.models import OutboxIntent
from notification_adapter.policy import require_policy

TYPES = {'NEAR_EXPIRY','LOW_STOCK','APPOINTMENT_REMINDER','APPOINTMENT_CANCELLED'}
CHANNELS = {'IN_APP','EMAIL_MOCK','SMS_MOCK'}
class EventConflict(Exception): pass

def _uuid(value):
    try: return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError): raise ValueError('A valid UUID is required.') from None

def _aware(value):
    if not isinstance(value,datetime) or timezone.is_naive(value): raise ValueError('An aware timestamp is required.')
    return value.astimezone(dt_timezone.utc)

def enqueue_intent(*, event_id, recipient_id, event_type: str, record_id, due_at, channels: list[str]) -> dict:
    require_policy('S2-06')
    if not connection.in_atomic_block: raise RuntimeError('enqueue_intent requires the caller atomic transaction.')
    event_id,recipient_id,record_id=map(_uuid,(event_id,recipient_id,record_id));due_at=_aware(due_at)
    if event_type not in TYPES: raise ValueError('Unsupported notification type.')
    if not isinstance(channels,list) or not channels or any(not isinstance(c,str) or c not in CHANNELS for c in channels) or len(set(channels))!=len(channels): raise ValueError('Invalid channels.')
    channels=sorted(channels)
    canonical={'event_id':str(event_id),'recipient_id':str(recipient_id),'type':event_type,'record_id':str(record_id),'due_at':due_at.isoformat(),'channels':channels}
    digest=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    try:
        with transaction.atomic():
            row=OutboxIntent.objects.create(event_id=event_id,recipient_id=recipient_id,event_type=event_type,record_id=record_id,due_at=due_at,channels=channels,payload_hash=digest,next_attempt_at=due_at)
    except IntegrityError:
        row=OutboxIntent.objects.filter(event_id=event_id).first()
        if row is None: raise
        if row.payload_hash!=digest: raise EventConflict('Event ID already has a different payload.') from None
    return {'id':str(row.pk),'event_id':str(row.event_id),'state':row.state}
