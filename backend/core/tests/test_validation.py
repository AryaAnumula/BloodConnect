"""BB-11 component tests. Proposed fields != approved feature implementation."""
from datetime import date
from io import BytesIO
from django.http import QueryDict
from django.test import SimpleTestCase
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework import serializers
from core.validation import StrictInputSerializer, validate_shared_input
from core.parsers import StrictJSONParser
from core.input_schemas import (LoginInputSerializer, RegistrationInputSerializer,
                               ScreeningInputSerializer, SearchInputSerializer)


def registration(**overrides):
    values = dict(email=' DONOR@EXAMPLE.TEST ', mobile='+919876543210',
                  password='synthetic-test-password', full_name="Synthetic O'Neil",
                  blood_group='O+', location='Synthetic City')
    return RegistrationInputSerializer(data=values | overrides)


class ValidationProviderTests(SimpleTestCase):
    def test_valid_candidate_registration_and_normalization(self):
        s = registration()
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['email'], 'donor@example.test')
        self.assertEqual(s.validated_data['mobile'], '+919876543210')
        self.assertEqual(s.validated_data['full_name'], "Synthetic O'Neil")

    def test_login_preserves_password_whitespace_and_hides_representation(self):
        s = LoginInputSerializer(data={'email': ' DONOR@EXAMPLE.TEST ', 'password': '  ExactCase!  '})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['password'], '  ExactCase!  ')
        self.assertNotIn('password', s.data)

    def test_json_strings_never_coerce_numeric_boolean_or_objects(self):
        for field in ['email', 'mobile', 'password', 'full_name', 'location', 'blood_group']:
            for value in [123456, True, False, [], {}, None]:
                with self.subTest(field=field, type=type(value).__name__):
                    self.assertFalse(registration(**{field: value}).is_valid())

    def test_required_fields_and_nulls(self):
        for field in registration().fields:
            data = dict(registration().initial_data)
            del data[field]
            with self.subTest(field=field):
                self.assertFalse(RegistrationInputSerializer(data=data).is_valid())

    def test_length_boundaries_120_and_121(self):
        for field in ['full_name', 'location']:
            good, bad = registration(**{field: 'x' * 120}), registration(**{field: 'x' * 121})
            self.assertTrue(good.is_valid(), good.errors)
            self.assertFalse(bad.is_valid())

    def test_candidate_registration_password_minimum_and_blanks(self):
        self.assertTrue(registration(password='x' * 12).is_valid())
        self.assertFalse(registration(password='x' * 11).is_valid())
        for field in ['email', 'mobile', 'password', 'full_name', 'location', 'blood_group']:
            self.assertFalse(registration(**{field: ''}).is_valid())

    def test_candidate_phone_boundaries_and_no_country_guessing(self):
        for mobile in ['+12345678', '+123456789012345']:
            s = registration(mobile=mobile)
            self.assertTrue(s.is_valid(), s.errors)
        for mobile in ['12345678', '+01234567', '+1234567', '+1234567890123456', '+12345678\nX']:
            self.assertFalse(registration(mobile=mobile).is_valid())

    def test_email_format_and_length(self):
        for email in ['not-an-email', 'a' * 255, 'x@example.test\r\nInjected: value']:
            self.assertFalse(registration(email=email).is_valid())

    def test_unknown_and_privilege_fields_rejected_without_echo(self):
        for field in ['role', 'is_staff', 'is_superuser', 'health_data', 'SYNTHETIC_UNTRUSTED_KEY']:
            s = registration(**{field: 'SYNTHETIC_SECRET_VALUE'})
            self.assertFalse(s.is_valid())
            self.assertNotIn(field, str(s.errors))
            self.assertNotIn('SYNTHETIC_SECRET_VALUE', str(s.errors))

    def test_read_only_input_is_not_silently_accepted(self):
        class Probe(StrictInputSerializer):
            id = serializers.CharField(read_only=True)
            name = serializers.CharField()
        self.assertFalse(Probe(data={'id': 'untrusted', 'name': 'Synthetic'}).is_valid())

    def test_non_object_payloads_rejected(self):
        for value in [[], 'text', 1, True, None]:
            self.assertFalse(LoginInputSerializer(data=value).is_valid())

    def test_choice_errors_do_not_echo_values(self):
        s = registration(blood_group='SYNTHETIC_SECRET_VALUE')
        self.assertFalse(s.is_valid())
        self.assertNotIn('SYNTHETIC_SECRET_VALUE', str(s.errors))

    def test_markup_is_literal_data_not_destructively_sanitized(self):
        value = '<b>Synthetic</b>'
        self.assertEqual(validate_shared_input(value=value, rule_name='location'), value)
        self.assertEqual(validate_shared_input(value="O'Neil", rule_name='full_name'), "O'Neil")

    def test_unknown_shared_rule_fails_without_echo(self):
        with self.assertRaises(ValidationError) as raised:
            validate_shared_input(value='SYNTHETIC_SECRET_VALUE', rule_name='unapproved')
        self.assertNotIn('SYNTHETIC_SECRET_VALUE', str(raised.exception))

    def test_screening_shape_does_not_decide_clinical_eligibility(self):
        s = ScreeningInputSerializer(data={'age_years': 0, 'weight_kg': '0.00', 'last_donation_date': None})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertNotIn('status', s.validated_data)

    def test_screening_json_integer_and_decimal_string_types(self):
        for age in [True, '25', 25.0, -1]:
            self.assertFalse(ScreeningInputSerializer(data={'age_years': age, 'weight_kg': '60', 'last_donation_date': None}).is_valid())
        for weight in [60, 60.0, True, 'NaN', '-1', '1.234', '60\nX', '1e2']:
            self.assertFalse(ScreeningInputSerializer(data={'age_years': 25, 'weight_kg': weight, 'last_donation_date': None}).is_valid())

    def test_screening_date_requires_real_iso_day_or_explicit_null(self):
        for value in ['2024-02-29', None]:
            s = ScreeningInputSerializer(data={'age_years': 25, 'weight_kg': '60', 'last_donation_date': value})
            self.assertTrue(s.is_valid(), s.errors)
        for value in ['2025-02-29', '01/02/2024', '2024-02-29T00:00:00Z', date(2024, 1, 1), 1, '']:
            self.assertFalse(ScreeningInputSerializer(data={'age_years': 25, 'weight_kg': '60', 'last_donation_date': value}).is_valid())
        self.assertFalse(ScreeningInputSerializer(data={'age_years': 25, 'weight_kg': '60'}).is_valid())

    def test_search_defaults_and_group_plus_encoding(self):
        s = SearchInputSerializer(data=QueryDict('blood_group=O%2B'))
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual((s.validated_data['blood_group'], s.validated_data['page'], s.validated_data['page_size']), ('O+', 1, 20))

    def test_search_pagination_boundaries_and_noninteger_strings(self):
        self.assertTrue(SearchInputSerializer(data={'page': '1', 'page_size': '100'}).is_valid())
        for values in [{'page': '0'}, {'page_size': '101'}, {'page': '1.0'},
                       {'page': True}, {'page': 1.5}, {'page': '1e2'}, {'page': '-1'}]:
            self.assertFalse(SearchInputSerializer(data=values).is_valid())

    def test_search_unknown_repeated_and_unapproved_values(self):
        for data in [QueryDict('page=1&page=2'), QueryDict('blood_group=O%2B&blood_group=A%2B'),
                     {'health_data': 'SYNTHETIC_SECRET'}, {'eligibility_status': 'UNKNOWN'}]:
            self.assertFalse(SearchInputSerializer(data=data).is_valid())

    def test_search_location_is_not_guessed_to_be_required(self):
        self.assertTrue(SearchInputSerializer(data={}).is_valid())
        self.assertTrue(SearchInputSerializer(data={'location': ''}).is_valid())
        self.assertFalse(SearchInputSerializer(data={'location': 'x' * 121}).is_valid())


class StrictParserTests(SimpleTestCase):
    def parse(self, raw):
        return StrictJSONParser().parse(BytesIO(raw))

    def test_valid_json_object_is_preserved(self):
        self.assertEqual(self.parse(b'{"a": 1, "b": {"x": true}}'), {'a': 1, 'b': {'x': True}})

    def test_top_level_and_nested_duplicate_keys_rejected(self):
        for raw in [b'{"password":"SYNTHETIC_SECRET","password":"other"}', b'{"a":{"x":1,"x":2}}']:
            with self.assertRaises(ParseError) as raised:
                self.parse(raw)
            self.assertNotIn('SYNTHETIC_SECRET', str(raised.exception))

    def test_malformed_nonfinite_and_invalid_utf8_are_redacted(self):
        for raw in [b'{"SYNTHETIC_SECRET":', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":"\xff"}']:
            with self.assertRaises(ParseError) as raised:
                self.parse(raw)
            self.assertNotIn('SYNTHETIC_SECRET', str(raised.exception))

    def test_exponent_overflow_rejected_at_any_depth(self):
        for raw in [b'1e999', b'{"x":-1e999}', b'{"a":[{"x":1e999}]}']:
            with self.subTest(raw=raw), self.assertRaises(ParseError):
                self.parse(raw)

    def test_finite_decimal_and_exponent_numbers_remain_supported(self):
        self.assertEqual(self.parse(b'{"x":1.25,"y":-2.5e3,"z":1e-300}'),
                         {'x': 1.25, 'y': -2500.0, 'z': 1e-300})

    def test_decoder_recursion_error_is_redacted_failure_injection(self):
        from unittest.mock import patch
        # Runtime JSON decoders differ in recursion handling; inject that failure
        # explicitly rather than inventing an unapproved nesting threshold.
        with patch('core.parsers.json.load', side_effect=RecursionError('PRIVATE_DECODER_DETAIL')):
            with self.assertRaises(ParseError) as raised:
                self.parse(b'{"a":1}')
        self.assertNotIn('PRIVATE_DECODER_DETAIL', str(raised.exception))
