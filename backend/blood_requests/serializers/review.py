"""BB-18 inputs (BC-D029-a/b): staff queue query and review decision body."""
from rest_framework import serializers

from core.validation import (QueryIntegerField, StrictChoiceField, StrictInputSerializer,
                             StrictStringField)

from blood_requests.models.request import STATUS_VALUES

DECISIONS = ('APPROVED', 'REJECTED')
REASON_MAX = 240


class StaffQueueQuerySerializer(StrictInputSerializer):
    """Exactly status, page, page_size; unknown or repeated keys are rejected."""
    status = StrictChoiceField(choices=STATUS_VALUES, required=False)
    page = QueryIntegerField(min_value=1, default=1)
    page_size = QueryIntegerField(min_value=1, max_value=100, default=20)

    def to_internal_value(self, data):
        # DRF treats a blank query value (?status=) as "omitted"; BC-D029-a requires 400.
        blank = [key for key in self.fields if hasattr(data, 'get') and data.get(key) == '']
        if blank:
            raise serializers.ValidationError({key: ['This field may not be blank.'] for key in blank})
        return super().to_internal_value(data)


class ReviewDecisionSerializer(StrictInputSerializer):
    """APPROVED: reason key must be absent. REJECTED: string reason, trimmed, 1..240."""
    status = StrictChoiceField(choices=DECISIONS)
    rejection_reason = StrictStringField(required=False, allow_null=True, allow_blank=False,
                                         trim_whitespace=True, max_length=REASON_MAX)

    def validate(self, attrs):
        has_reason_key = 'rejection_reason' in self.initial_data
        if attrs['status'] == 'APPROVED':
            if has_reason_key:
                raise serializers.ValidationError(
                    {'rejection_reason': ['Leave out the rejection reason when approving.']})
            attrs['rejection_reason'] = None
            return attrs
        if attrs.get('rejection_reason') is None:
            raise serializers.ValidationError(
                {'rejection_reason': ['A rejection reason is required.']})
        return attrs
