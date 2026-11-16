import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class InventoryDisposition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField('inventory.BloodUnit', on_delete=models.PROTECT, related_name='disposition')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inventory_dispositions')
    from_status = models.CharField(max_length=16, default='AVAILABLE')
    to_status = models.CharField(max_length=16, choices=[('DISCARDED', 'Discarded'), ('QUARANTINED', 'Quarantined')])
    reason = models.CharField(max_length=240)
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(from_status='AVAILABLE'), name='inventory_disposition_from'),
            models.CheckConstraint(condition=models.Q(to_status__in=('DISCARDED', 'QUARANTINED')), name='inventory_disposition_to'),
            models.CheckConstraint(condition=~models.Q(reason=''), name='inventory_disposition_reason'),
        ]
