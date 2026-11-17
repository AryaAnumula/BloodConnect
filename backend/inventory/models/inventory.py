
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from core.input_schemas import BLOOD_GROUPS

GROUP_CHOICES = tuple((g, g) for g in BLOOD_GROUPS)


class CollectionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(
        "donors.DonorProfile",
        on_delete=models.PROTECT,
        related_name="collection_events",
    )
    collection_date = models.DateField()
    blood_group = models.CharField(max_length=3, choices=GROUP_CHOICES)
    status = models.CharField(max_length=16, default="CONFIRMED")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="recorded_collection_events")
    confirmed_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-collection_date", "-confirmed_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(status="CONFIRMED"), name="inventory_event_confirmed"),
            models.CheckConstraint(condition=models.Q(blood_group__in=BLOOD_GROUPS), name="inventory_event_group"),
        ]
        indexes = [
            models.Index(fields=["donor", "collection_date"]),
        ]

    def __str__(self):
        return f"{self.donor_id} - {self.collection_date}"


class BloodUnit(models.Model):
    class Component(models.TextChoices):
        WHOLE_BLOOD = "WHOLE_BLOOD", "Whole blood"
        RBC = "RBC", "Red blood cells"
        PLASMA = "PLASMA", "Plasma"
        PLATELETS = "PLATELETS", "Platelets"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ISSUED = "ISSUED", "Issued"
        DISCARDED = "DISCARDED", "Discarded"
        QUARANTINED = "QUARANTINED", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_code = models.CharField(max_length=64, unique=True)
    donor = models.ForeignKey("donors.DonorProfile", on_delete=models.PROTECT,
                              related_name="blood_units")
    collection_event = models.ForeignKey(
        CollectionEvent,
        on_delete=models.PROTECT,
        related_name="units",
    )
    blood_group = models.CharField(max_length=3, choices=GROUP_CHOICES)
    component_type = models.CharField(max_length=16, choices=Component.choices)
    collection_date = models.DateField()
    expiry_date = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(unit_code=""), name="inventory_unit_code_nonempty"),
            models.CheckConstraint(condition=models.Q(blood_group__in=BLOOD_GROUPS), name="inventory_unit_group"),
            models.CheckConstraint(condition=models.Q(component_type__in=("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")), name="inventory_unit_component"),
            models.CheckConstraint(condition=models.Q(status__in=("AVAILABLE", "ISSUED", "DISCARDED", "QUARANTINED")), name="inventory_unit_status"),
            models.CheckConstraint(
                condition=models.Q(quantity=1),
                name="inventory_unit_quantity_one",
            ),
            models.CheckConstraint(
                condition=models.Q(expiry_date__gt=models.F("collection_date")),
                name="inventory_expiry_after_collection",
            ),
            models.UniqueConstraint(
                fields=["collection_event", "component_type"],
                name="inventory_event_component_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["blood_group", "component_type", "status"]),
            models.Index(fields=["status", "expiry_date"]),
        ]

    def __str__(self):
        return self.unit_code
