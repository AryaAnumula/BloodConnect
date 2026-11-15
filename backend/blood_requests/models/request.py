"""BB-17 BloodRequest. Writer: Arnav. Approved scope: BC-D017–BC-D022 (15 Nov 2026).

Components and the 1–100 whole-unit quantity range are the approved college-demo values,
enforced again by database constraints. The requester is PROTECTed: request history is
never deleted with an account; accounts are deactivated instead. Review, issue and closure
semantics (BB-18/16/19) are not decided here; only the status vocabulary exists.
"""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from core.input_schemas import BLOOD_GROUPS

MAX_REQUEST_QUANTITY = 100  # approved college-demo limit, not a clinical limit
COMPONENT_TYPES = ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS')
URGENCY_VALUES = ('CRITICAL', 'URGENT', 'ROUTINE')
STATUS_VALUES = ('SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED')


class BloodRequest(models.Model):
    class ComponentType(models.TextChoices):
        WHOLE_BLOOD = 'WHOLE_BLOOD', 'Whole blood'
        RBC = 'RBC', 'Red blood cells'
        PLASMA = 'PLASMA', 'Plasma'
        PLATELETS = 'PLATELETS', 'Platelets'

    class Urgency(models.TextChoices):
        CRITICAL = 'CRITICAL', 'Critical'
        URGENT = 'URGENT', 'Urgent'
        ROUTINE = 'ROUTINE', 'Routine'

    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        ISSUED = 'ISSUED', 'Issued'
        CLOSED = 'CLOSED', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name='blood_requests')
    blood_group = models.CharField(max_length=3, choices=[(g, g) for g in BLOOD_GROUPS])
    component_type = models.CharField(max_length=16, choices=ComponentType.choices)
    quantity = models.PositiveIntegerField()
    fulfilled_quantity = models.PositiveIntegerField(default=0)
    urgency_level = models.CharField(max_length=8, choices=Urgency.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    rejection_reason = models.CharField(max_length=240, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['status', 'urgency_level', 'created_at'], name='blood_req_queue_idx'),
            models.Index(fields=['requester', 'created_at'], name='blood_req_owner_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1, quantity__lte=MAX_REQUEST_QUANTITY),
                name='blood_request_quantity_range'),
            models.CheckConstraint(
                condition=Q(fulfilled_quantity__gte=0, fulfilled_quantity__lte=F('quantity')),
                name='blood_request_fulfilled_range'),
            models.CheckConstraint(condition=Q(blood_group__in=BLOOD_GROUPS),
                                   name='blood_request_blood_group_valid'),
            models.CheckConstraint(condition=Q(component_type__in=COMPONENT_TYPES),
                                   name='blood_request_component_valid'),
            models.CheckConstraint(condition=Q(urgency_level__in=URGENCY_VALUES),
                                   name='blood_request_urgency_valid'),
            models.CheckConstraint(condition=Q(status__in=STATUS_VALUES),
                                   name='blood_request_status_valid'),
        ]

    def __str__(self):
        return str(self.id)  # no requester email or other personal data
