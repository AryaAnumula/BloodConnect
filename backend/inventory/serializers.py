from uuid import UUID

from rest_framework import serializers

from core.input_schemas import BLOOD_GROUPS
from core.validation import (StrictInputSerializer, StrictStringField, StrictChoiceField,
                             StrictIntegerField, ISODateField, QueryIntegerField)
from inventory.services.policy import SUPPORTED_COMPONENTS


class InventoryUUIDField(serializers.UUIDField):
    def to_internal_value(self, value):
        if not isinstance(value, (str, UUID)):
            self.fail('invalid')
        return super().to_internal_value(value)


class BloodUnitCreate(StrictInputSerializer):
    unit_code = StrictStringField(min_length=1, max_length=64)
    donor_id = InventoryUUIDField()
    collection_event_id = InventoryUUIDField(required=False)
    blood_group = StrictChoiceField(choices=BLOOD_GROUPS)
    component_type = StrictChoiceField(choices=SUPPORTED_COMPONENTS)
    collection_date = ISODateField()
    quantity = StrictIntegerField(min_value=1, max_value=1)


class StockQuery(StrictInputSerializer):
    blood_group = StrictChoiceField(choices=BLOOD_GROUPS, required=False)
    component_type = StrictChoiceField(choices=SUPPORTED_COMPONENTS, required=False)
    page = QueryIntegerField(min_value=1, default=1)
    page_size = QueryIntegerField(min_value=1, max_value=100, default=20)


class UnitQuery(StockQuery):
    status = StrictChoiceField(choices=('AVAILABLE', 'ISSUED', 'DISCARDED', 'QUARANTINED', 'EXPIRED'), required=False)


class DispositionCreate(StrictInputSerializer):
    status = StrictChoiceField(choices=('DISCARDED', 'QUARANTINED'))
    reason = StrictStringField(min_length=1, max_length=240)
