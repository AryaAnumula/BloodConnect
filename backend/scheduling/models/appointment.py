"""BB-21 Appointment. PROPOSED per docs/sprint2/models-and-migrations.md; S2-05 approval pending.

The donor is always the authenticated donor's profile, never client supplied. PROTECT on donor
and slot: deletion/retention of booking history is not approved, so nothing cascades silently.
The partial unique constraint is the final guard against a duplicate active booking.
"""
import uuid

from django.db import models
from django.db.models import Q


class Appointment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey('donors.DonorProfile', on_delete=models.PROTECT,
                              related_name='appointments')
    slot = models.ForeignKey('scheduling.Slot', on_delete=models.PROTECT,
                             related_name='appointments')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['slot', 'status']),
                   models.Index(fields=['donor', 'status'])]
        constraints = [
            models.UniqueConstraint(
                fields=['donor', 'slot'], condition=Q(status='CONFIRMED'),
                name='appointment_one_active_per_donor_slot'),
        ]

    def __str__(self):
        return str(self.id)
