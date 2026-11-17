"""BB-21 slot setup. Walk-in slots have no camp. A camp slot must lie inside the camp's interval
and the capacities of its OPEN slots may not exceed the camp capacity (checked under the camp lock).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from scheduling.dto import slot_dto
from scheduling.exceptions import CampNotActive, CapacityConflict
from scheduling.models import Camp, Slot
from scheduling.permissions import require_camp_role


def create_slot(*, actor, data: dict) -> dict:
    require_camp_role(user=actor, action='slot_create')
    camp_id = data['camp_id']
    with transaction.atomic():
        camp = None
        if camp_id is not None:
            try:
                camp = Camp.objects.select_for_update().get(pk=camp_id)
            except (Camp.DoesNotExist, DjangoValidationError, ValueError):
                raise NotFound() from None
            if camp.status != Camp.Status.ACTIVE:
                raise CampNotActive()
            if data['starts_at'] < camp.starts_at or data['ends_at'] > camp.ends_at:
                raise ValidationError({'starts_at': ['The slot must be inside the camp times.']})
            booked_capacity = sum(
                Slot.objects.filter(camp=camp, status=Slot.Status.OPEN)
                .values_list('capacity', flat=True))
            if booked_capacity + data['capacity'] > camp.capacity:
                raise CapacityConflict('The camp does not have enough capacity for this slot.')
        slot = Slot.objects.create(
            camp=camp, location=data['location'], starts_at=data['starts_at'],
            ends_at=data['ends_at'], capacity=data['capacity'])
    return slot_dto(slot, 0)
