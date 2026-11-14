from datetime import datetime, timezone

from django.http import QueryDict
from django.test import SimpleTestCase

from scheduling.camp_inputs import (CampCreateInputSerializer, CampListInputSerializer,
                                    CampUpdateInputSerializer)

VALID = {
    'name': 'City Hall Camp',
    'location': 'Chennai',
    'starts_at': '2026-12-01T10:00:00+05:30',
    'ends_at': '2026-12-01T16:00:00+05:30',
    'capacity': 40,
}


def create(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return CampCreateInputSerializer(data=data)


class CampCreateInputTests(SimpleTestCase):
    def test_valid_input_and_offsets_are_converted_to_utc(self):
        s = create()
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['starts_at'],
                         datetime(2026, 12, 1, 4, 30, tzinfo=timezone.utc))
        self.assertEqual(s.validated_data['capacity'], 40)

    def test_z_suffix_is_accepted(self):
        s = create(starts_at='2026-12-01T10:00:00Z', ends_at='2026-12-01T12:00:00Z')
        self.assertTrue(s.is_valid(), s.errors)

    def test_naive_and_malformed_datetimes_rejected(self):
        for bad in ('2026-12-01T10:00:00', '2026-12-01', '01/12/2026 10:00',
                    '2026-13-45T10:00:00Z', 'not-a-date', '', 12345, None, ['x']):
            with self.subTest(value=bad):
                self.assertFalse(create(starts_at=bad).is_valid())
                self.assertFalse(create(ends_at=bad).is_valid())

    def test_start_must_be_before_end(self):
        same = '2026-12-01T10:00:00+05:30'
        self.assertFalse(create(starts_at=same, ends_at=same).is_valid())
        self.assertFalse(create(starts_at='2026-12-01T16:00:00+05:30',
                                ends_at='2026-12-01T10:00:00+05:30').is_valid())

    def test_text_fields_rejected_when_blank_too_long_or_not_strings(self):
        for field in ('name', 'location'):
            for bad in ('', '   ', 'x' * 121, 123, True, None, ['a']):
                with self.subTest(field=field, value=bad):
                    self.assertFalse(create(**{field: bad}).is_valid())

    def test_text_fields_are_trimmed(self):
        s = create(name='  Camp  ', location=' Hall ')
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['name'], 'Camp')
        self.assertEqual(s.validated_data['location'], 'Hall')

    def test_capacity_must_be_a_positive_whole_number(self):
        for bad in (0, -1, '5', True, 5.5, 5.0, None, 2147483648):
            with self.subTest(value=bad):
                self.assertFalse(create(capacity=bad).is_valid())
        self.assertTrue(create(capacity=1).is_valid())

    def test_missing_fields_rejected(self):
        for name in VALID:
            data = {k: v for k, v in VALID.items() if k != name}
            with self.subTest(missing=name):
                s = CampCreateInputSerializer(data=data)
                self.assertFalse(s.is_valid())
                self.assertIn(name, s.errors)

    def test_unknown_and_read_only_fields_rejected(self):
        for extra in ({'status': 'CANCELLED'}, {'id': 'x'}, {'role': 'ADMIN'}, {'extra': 1}):
            with self.subTest(extra=extra):
                s = create(**extra)
                self.assertFalse(s.is_valid())
                self.assertIn('non_field_errors', s.errors)

    def test_non_object_input_rejected(self):
        self.assertFalse(CampCreateInputSerializer(data=['x']).is_valid())


class CampUpdateInputTests(SimpleTestCase):
    def test_partial_update_is_valid(self):
        s = CampUpdateInputSerializer(data={'capacity': 10})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data, {'capacity': 10})

    def test_empty_update_rejected(self):
        s = CampUpdateInputSerializer(data={})
        self.assertFalse(s.is_valid())
        self.assertIn('non_field_errors', s.errors)

    def test_unknown_and_invalid_fields_rejected(self):
        for payload in ({'status': 'CANCELLED'}, {'capacity': 0}, {'name': ''},
                        {'starts_at': '2026-12-01T10:00:00'}):
            with self.subTest(payload=payload):
                self.assertFalse(CampUpdateInputSerializer(data=payload).is_valid())


class CampListInputTests(SimpleTestCase):
    def test_defaults(self):
        s = CampListInputSerializer(data=QueryDict(''))
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['page'], 1)
        self.assertEqual(s.validated_data['page_size'], 20)

    def test_valid_filters(self):
        s = CampListInputSerializer(data=QueryDict('status=ACTIVE&page=2&page_size=50'))
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['status'], 'ACTIVE')

    def test_invalid_values_rejected(self):
        for query in ('status=OPEN', 'page=0', 'page=abc', 'page=1.5', 'page_size=101',
                      'page_size=0', 'unknown=1'):
            with self.subTest(query=query):
                self.assertFalse(CampListInputSerializer(data=QueryDict(query)).is_valid())

    def test_repeated_query_values_rejected(self):
        s = CampListInputSerializer(data=QueryDict('status=ACTIVE&status=CANCELLED'))
        self.assertFalse(s.is_valid())
