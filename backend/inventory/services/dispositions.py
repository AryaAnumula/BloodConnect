from django.db import DatabaseError, transaction
from rest_framework.exceptions import NotFound

from inventory.exceptions import InventoryUnavailable, InvalidTransition
from inventory.models import BloodUnit, InventoryDisposition
from inventory.permissions import require_staff
from inventory.serializers import DispositionCreate
from inventory.services.units import unit_dto


def record_disposition(*, actor, unit_id, data):
    require_staff(actor)
    serializer = DispositionCreate(data=data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    try:
        with transaction.atomic():
            try:
                unit = BloodUnit.objects.select_for_update().get(pk=unit_id)
            except BloodUnit.DoesNotExist:
                raise NotFound() from None
            if unit.status != 'AVAILABLE':
                raise InvalidTransition()
            InventoryDisposition.objects.create(unit=unit, actor=actor, from_status=unit.status,
                to_status=values['status'], reason=values['reason'])
            unit.status = values['status']
            unit.save(update_fields=['status'])
            return unit_dto(unit)
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
