"""BB-16 IssueRecord. Writer: Arnav, only through blood_requests.services.issue.

One row per issued unit (the OneToOne unit FK makes a second issue of the same unit a
database conflict). Request, unit and issuer are PROTECTed: issue history is never
deleted with an account, request or unit. issued_quantity is fixed at 1 (contract v1.1).
"""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class IssueRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey('blood_requests.BloodRequest', on_delete=models.PROTECT, related_name='issues')
    unit = models.OneToOneField('inventory.BloodUnit', on_delete=models.PROTECT, related_name='issue_record')
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name='issued_blood_units')
    issued_at = models.DateTimeField()  # aware server time taken by issue_request after the request lock
    issued_quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['issued_at', 'id']
        indexes = [models.Index(fields=['issued_at'], name='issue_record_time_idx')]
        constraints = [models.CheckConstraint(condition=Q(issued_quantity=1), name='issue_record_quantity_one')]
