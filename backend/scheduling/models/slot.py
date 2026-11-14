"""BB-21 Slot. PROPOSED per docs/sprint2/models-and-migrations.md; S2-05 approval pending.

camp is optional: a slot without a camp is a walk-in slot. PROTECT on camp: no hidden cascade
deletion of operational history (deletion/retention policy is not approved).
"""
import uuid

from django.db import models
from django.db.models import F, Q


class Slot(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    camp = models.ForeignKey('scheduling.Camp', null=True, blank=True,
                             on_delete=models.PROTECT, related_name='slots')
    location = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at', 'id']
        indexes = [models.Index(fields=['status', 'starts_at']),
                   models.Index(fields=['camp', 'starts_at'])]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='slot_capacity_positive'),
            models.CheckConstraint(condition=Q(starts_at__lt=F('ends_at')),
                                   name='slot_starts_before_ends'),
        ]

    def __str__(self):
        return str(self.id)
