"""BB-20 Camp. PROPOSED fields per docs/sprint2/openapi.proposed.yaml (Camp).

S2-04 (roles) and S2-05 (capacity/cancellation) approval pending.
"""
import uuid

from django.db import models
from django.db.models import F, Q


class Camp(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    cancel_reason = models.CharField(max_length=240, blank=True, default='')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at', 'id']
        indexes = [models.Index(fields=['status', 'starts_at'])]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='camp_capacity_positive'),
            models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')),
                                   name='camp_starts_before_ends'),
        ]

    def __str__(self):
        return str(self.id)
