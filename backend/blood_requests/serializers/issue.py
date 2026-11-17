"""BB-16 IssueCreate input (BC-D026): {"unit_ids": [<UUID>, ...]}, 1..100 unique units.

Only unit_ids is accepted; actor, status, quantities and timestamps are server-controlled.
Ids are canonical lowercase UUID strings; duplicates in one payload are rejected (400).
Whether the batch fits the request's remaining quantity is checked under the request lock.
"""
import re

from rest_framework import serializers

from core.validation import StrictInputSerializer, StrictStringField

MAX_BATCH = 100
UUID_TEXT = re.compile(r'\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z')


def clean_unit_ids(values) -> list[str]:
    """Shared by the serializer and the service boundary. Returns sorted canonical ids."""
    if not isinstance(values, (list, tuple)):
        raise serializers.ValidationError({'unit_ids': ['Provide a list of unit IDs.']})
    if not 1 <= len(values) <= MAX_BATCH:
        raise serializers.ValidationError({'unit_ids': [f'Select between 1 and {MAX_BATCH} units.']})
    cleaned = []
    for value in values:
        if not isinstance(value, str) or not UUID_TEXT.match(value):
            raise serializers.ValidationError({'unit_ids': ['Each unit ID must be a UUID.']})
        cleaned.append(value.lower())
    if len(set(cleaned)) != len(cleaned):
        raise serializers.ValidationError({'unit_ids': ['Each unit may be selected only once.']})
    return sorted(cleaned)


class IssueCreateSerializer(StrictInputSerializer):
    unit_ids = serializers.ListField(child=StrictStringField(trim_whitespace=False), allow_empty=True)

    def validate_unit_ids(self, value):
        try:
            return clean_unit_ids(value)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError(exc.detail['unit_ids']) from None
