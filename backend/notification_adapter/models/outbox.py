import uuid
from django.db import models
from django.db.models import Q

class OutboxIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    recipient_id = models.UUIDField()
    event_type = models.CharField(max_length=32)
    record_id = models.UUIDField()
    due_at = models.DateTimeField()
    channels = models.JSONField()
    payload_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=12, default='PENDING')
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    lease_token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    delivered_at = models.DateTimeField(null=True)
    last_error_code = models.CharField(max_length=48, blank=True)
    scheduled_for = models.DateTimeField(null=True)
    late_booking = models.BooleanField(default=False)
    timing_met = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['state', 'next_attempt_at'], name='notif_due_state_idx')]
        constraints = [models.CheckConstraint(condition=Q(state__in=['PENDING','LEASED','BLOCKED','DELIVERED','FAILED','CANCELLED']), name='notif_valid_state'), models.CheckConstraint(condition=Q(event_type__in=['NEAR_EXPIRY','LOW_STOCK','APPOINTMENT_REMINDER','APPOINTMENT_CANCELLED']), name='notif_valid_type')]

class DeliveryAttempt(models.Model):
    intent = models.ForeignKey(OutboxIntent, on_delete=models.CASCADE, related_name='delivery_attempts')
    # Nullable for records created before channel-level evidence was introduced.
    channel = models.CharField(max_length=16, null=True, blank=True)
    receipt_key = models.CharField(max_length=60, null=True, blank=True)
    attempted_at = models.DateTimeField()
    outcome = models.CharField(max_length=16)
    error_code = models.CharField(max_length=48, blank=True)
    # No request/response bodies, addresses, passwords, tokens or health answers.
