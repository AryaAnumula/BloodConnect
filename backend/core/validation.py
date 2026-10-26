"""BB-11 reusable validation. Candidate D-05 conventions are NOT approval.

Feature owners validate before calling services; this module does not change routes,
permissions, database uniqueness, password policy or clinical decisions.
"""
from collections.abc import Mapping
import re
from rest_framework import serializers


class StrictInputSerializer(serializers.Serializer):
    """Object-only input, unknown/read-only keys and repeated query values rejected.

    Errors describe rules, never echo attacker-controlled keys or values.
    JSON duplicate-key handling belongs to core.parsers.StrictJSONParser.
    """
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({'non_field_errors': ['A JSON object is required.']})
        allowed = {name for name, field in self.fields.items() if not field.read_only}
        if set(data) - allowed:
            raise serializers.ValidationError({'non_field_errors': ['Unexpected input field.']})
        if hasattr(data, 'getlist') and any(len(data.getlist(key)) != 1 for key in data):
            raise serializers.ValidationError({'non_field_errors': ['Repeated input fields are not permitted.']})
        return super().to_internal_value(data)


class StrictStringField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid')
        return super().to_internal_value(data)


class StrictEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid')
        return super().to_internal_value(data)


class StrictChoiceField(serializers.ChoiceField):
    default_error_messages = {'invalid_choice': 'Select a permitted value.'}

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid_choice')
        return super().to_internal_value(data)


class StrictRegexField(serializers.RegexField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid')
        return super().to_internal_value(data)


class StrictIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, int):
            self.fail('invalid')
        return super().to_internal_value(data)


class QueryIntegerField(serializers.IntegerField):
    """Query strings contain decimal digits, not 1.0, booleans or exponent syntax."""
    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (str, int)):
            self.fail('invalid')
        if isinstance(data, str) and re.fullmatch(r'[0-9]+', data) is None:
            self.fail('invalid')
        return super().to_internal_value(data)


class ISODateField(serializers.DateField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', data) is None:
            self.fail('invalid', format='YYYY-MM-DD')
        return super().to_internal_value(data)


def normalize_email(value):
    """Candidate existing D-05/BB-01 trim + lowercase, no credential lookup."""
    return StrictEmailField(max_length=254).run_validation(value).strip().lower()


def normalize_mobile(value):
    """Candidate existing D-05 E.164, no inferred country code."""
    return StrictRegexField(regex=r'\A\+[1-9][0-9]{7,14}\Z', max_length=16,
                            trim_whitespace=True).run_validation(value)


def validate_shared_input(*, value, rule_name: str):
    """Return validated value; DRF ValidationError, no database/transaction side effects.

    Only agreed ingress should call these after D-05 review; no blanket HTML/SQL
    stripping. Keep legitimate punctuation; use ORM and contextual safe rendering.
    """
    if rule_name == 'email':
        return normalize_email(value)
    if rule_name == 'mobile':
        return normalize_mobile(value)
    if rule_name in ('full_name', 'location'):
        return StrictStringField(max_length=120, allow_blank=False).run_validation(value)
    raise serializers.ValidationError({'non_field_errors': ['Unknown validation rule.']})
