import uuid
from django.db import models
from django.utils import timezone


class AlertSweep(models.Model):
    """One durable serialization row for controlled alert sweeps."""
    key = models.CharField(max_length=32, primary_key=True)
    evaluated_at = models.DateTimeField(null=True)


class InventoryAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condition_key = models.CharField(max_length=100)
    policy_fingerprint = models.CharField(max_length=64)
    kind = models.CharField(max_length=16, choices=[('LOW_STOCK', 'Low stock'), ('NEAR_EXPIRY', 'Near expiry')])
    blood_group = models.CharField(max_length=3)
    component_type = models.CharField(max_length=16)
    unit = models.ForeignKey('inventory.BloodUnit', on_delete=models.PROTECT, null=True)
    intent = models.OneToOneField('notification_adapter.OutboxIntent', on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    resolved_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['condition_key'], condition=models.Q(active=True), name='inventory_alert_active_episode'),
            models.CheckConstraint(condition=models.Q(kind__in=('LOW_STOCK', 'NEAR_EXPIRY')), name='inventory_alert_kind'),
            models.CheckConstraint(condition=(models.Q(active=True, resolved_at__isnull=True) | models.Q(active=False, resolved_at__isnull=False)), name='inventory_alert_resolution'),
        ]
