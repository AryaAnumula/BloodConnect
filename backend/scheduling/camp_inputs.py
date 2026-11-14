"""BB-20 strict input contracts for camps (CampCreate, CampUpdate, camp list query).

Reuses the BB-11 strict fields. Unknown fields are rejected. Date-times must be ISO 8601 with an
explicit timezone offset; naive values are rejected and aware values are converted to UTC.
No past-date rule and no business maximum capacity: those are not approved yet.
"""
import re
from datetime import timezone as dt_timezone

from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from core.validation import (QueryIntegerField, StrictChoiceField, StrictInputSerializer,
                             StrictIntegerField, StrictStringField)

MAX_DB_INTEGER = 2147483647  # technical bound of the integer column, NOT a business rule
OFFSET_PATTERN = re.compile(r'(?:Z|[+-][0-9]{2}:[0-9]{2})\Z')


class AwareDateTimeField(serializers.DateTimeField):
    default_error_messages = {'invalid': 'Enter an ISO 8601 date-time with a timezone offset.'}

    def to_internal_value(self, value):
        if not isinstance(value, str):
            self.fail('invalid')
        text = value.strip()
        if OFFSET_PATTERN.search(text) is None:
            self.fail('invalid')
        try:
            parsed = parse_datetime(text)
        except ValueError:
            self.fail('invalid')
        if parsed is None or parsed.tzinfo is None:
            self.fail('invalid')
        return parsed.astimezone(dt_timezone.utc)


class CampCreateInputSerializer(StrictInputSerializer):
    name = StrictStringField(min_length=1, max_length=120)
    location = StrictStringField(min_length=1, max_length=120)
    starts_at = AwareDateTimeField()
    ends_at = AwareDateTimeField()
    capacity = StrictIntegerField(min_value=1, max_value=MAX_DB_INTEGER)

    def validate(self, attrs):
        if attrs['starts_at'] >= attrs['ends_at']:
            raise serializers.ValidationError({'ends_at': ['End must be after start.']})
        return attrs


class CampUpdateInputSerializer(StrictInputSerializer):
    name = StrictStringField(min_length=1, max_length=120, required=False)
    location = StrictStringField(min_length=1, max_length=120, required=False)
    starts_at = AwareDateTimeField(required=False)
    ends_at = AwareDateTimeField(required=False)
    capacity = StrictIntegerField(min_value=1, max_value=MAX_DB_INTEGER, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                {'non_field_errors': ['Provide at least one field to change.']})
        return attrs


class CampListInputSerializer(StrictInputSerializer):
    status = StrictChoiceField(choices=('ACTIVE', 'CANCELLED'), required=False)
    page = QueryIntegerField(min_value=1, default=1)
    page_size = QueryIntegerField(min_value=1, max_value=100, default=20)
