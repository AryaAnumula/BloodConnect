"""BB11 shared input contracts.
Real login/registration/screening use these now. SearchInputSerializer is supplied
but the BB09 search controller is still a stub on this baseline. Shapes do not
authorize callers,decide eligibility or enforce database uniqueness.
"""
from rest_framework import serializers
from .validation import (StrictInputSerializer, StrictStringField, StrictEmailField,
                         StrictChoiceField, StrictRegexField, StrictIntegerField,
                         QueryIntegerField, ISODateField, normalize_email, normalize_mobile)

BLOOD_GROUPS = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
ELIGIBILITY_STATES = ('ELIGIBLE', 'INELIGIBLE', 'NOT_SCREENED', 'STALE')


class LoginInputSerializer(StrictInputSerializer):
    email = StrictEmailField(max_length=254)
    # Preserve exact password bytes represented by the input string. No trim/lowercase.
    # No guessed maximum: OpenAPI has none. D-04 should resolve ingress/hash-cost bounds.
    password = StrictStringField(write_only=True, trim_whitespace=False, allow_blank=False)

    def validate_email(self, value):
        return normalize_email(value)


class RegistrationInputSerializer(StrictInputSerializer):
    email = StrictEmailField(max_length=254)
    mobile = StrictStringField(max_length=16)
    password = StrictStringField(min_length=12, write_only=True, trim_whitespace=False)
    full_name = StrictStringField(min_length=1, max_length=120, allow_blank=False)
    blood_group = StrictChoiceField(choices=BLOOD_GROUPS)
    location = StrictStringField(min_length=1, max_length=120, allow_blank=False)

    def validate_email(self, value):
        return normalize_email(value)

    def validate_mobile(self, value):
        return normalize_mobile(value)


class ScreeningInputSerializer(StrictInputSerializer):
    age_years = StrictIntegerField(min_value=0)
    weight_kg = StrictRegexField(regex=r'\A[0-9]+(\.[0-9]{1,2})?\Z', trim_whitespace=False)
    last_donation_date = ISODateField(allow_null=True)
    # Zero age/weight can pass shape validation, NOT clinical eligibility.
    # Null/first-time/freshness/medical rules remain D-07/D-08 decisions.


class SearchInputSerializer(StrictInputSerializer):
    blood_group = StrictChoiceField(choices=BLOOD_GROUPS, required=False)
    location = StrictStringField(max_length=120, allow_blank=True, required=False)
    eligibility_status = StrictChoiceField(choices=ELIGIBILITY_STATES, required=False)
    page = QueryIntegerField(min_value=1, default=1)
    page_size = QueryIntegerField(min_value=1, max_value=100, default=20)
