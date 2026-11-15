"""BB-17: RequestCreate input validation in isolation (no database, no route).

SYNTHETIC_POLICY deliberately uses max 10 (not the approved 100) to prove the serializer
follows whatever policy it is given. The approved values are tested in
test_configuration.py and end-to-end in test_create_api.py.
"""
from django.test import SimpleTestCase

from blood_requests.policy import RequestInputPolicy, require_policy
from blood_requests.serializers import RequestCreateSerializer
from core.errors import DecisionRequired

SYNTHETIC_POLICY = RequestInputPolicy(
    component_types=('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'), max_quantity=10)
VALID = {'blood_group': 'O-', 'component_type': 'RBC', 'quantity': 2, 'urgency_level': 'URGENT'}


def check(data, policy=SYNTHETIC_POLICY):
    serializer = RequestCreateSerializer(data=data, policy=policy)
    return serializer.is_valid(), serializer


class ValidInputTests(SimpleTestCase):
    def test_valid_input_returns_exactly_the_four_fields(self):
        ok, s = check(VALID)
        self.assertTrue(ok, s.errors)
        self.assertEqual(dict(s.validated_data), VALID)

    def test_every_blood_group_component_and_urgency_is_accepted(self):
        for group in ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'):
            for component in SYNTHETIC_POLICY.component_types:
                for urgency in ('CRITICAL', 'URGENT', 'ROUTINE'):
                    with self.subTest(group=group, component=component, urgency=urgency):
                        ok, s = check({**VALID, 'blood_group': group,
                                       'component_type': component, 'urgency_level': urgency})
                        self.assertTrue(ok, s.errors)

    def test_quantity_boundaries_one_and_maximum_are_accepted(self):
        for quantity in (1, SYNTHETIC_POLICY.max_quantity):
            with self.subTest(quantity=quantity):
                self.assertTrue(check({**VALID, 'quantity': quantity})[0])


class MissingAndEmptyFieldTests(SimpleTestCase):
    def test_each_missing_field_is_reported_by_name(self):
        for name in VALID:
            with self.subTest(missing=name):
                data = {k: v for k, v in VALID.items() if k != name}
                ok, s = check(data)
                self.assertFalse(ok)
                self.assertEqual(list(s.errors), [name])

    def test_empty_body_reports_all_four_fields(self):
        ok, s = check({})
        self.assertFalse(ok)
        self.assertEqual(set(s.errors), set(VALID))

    def test_empty_and_null_values_are_rejected(self):
        for name in VALID:
            for bad in ('', None):
                with self.subTest(field=name, value=bad):
                    ok, s = check({**VALID, name: bad})
                    self.assertFalse(ok)
                    self.assertIn(name, s.errors)

    def test_non_object_body_is_rejected(self):
        for body in ([], 'RBC', 5, None):
            with self.subTest(body=body):
                ok, s = check(body)
                self.assertFalse(ok)


class UnsupportedValueTests(SimpleTestCase):
    def test_unsupported_choices_are_rejected_without_echoing_the_value(self):
        cases = {
            'blood_group': ['C+', 'o-', 'O', ' O-', 'O- ', 'A+B'],
            'component_type': ['rbc', 'PLASMA ', 'CRYO', 'WHOLE BLOOD', 'whole_blood'],
            'urgency_level': ['critical', 'HIGH', 'STAT', 'Urgent'],
        }
        for name, values in cases.items():
            for bad in values:
                with self.subTest(field=name, value=bad):
                    ok, s = check({**VALID, name: bad})
                    self.assertFalse(ok)
                    self.assertEqual(list(s.errors), [name])
                    self.assertNotIn(bad, ' '.join(map(str, s.errors[name])))

    def test_wrong_json_types_for_choices_are_rejected(self):
        for name in ('blood_group', 'component_type', 'urgency_level'):
            for bad in (1, True, ['RBC'], {'v': 'RBC'}):
                with self.subTest(field=name, value=bad):
                    self.assertFalse(check({**VALID, name: bad})[0])

    def test_component_outside_the_injected_policy_is_rejected(self):
        three = RequestInputPolicy(component_types=('RBC', 'PLASMA', 'PLATELETS'), max_quantity=10)
        self.assertFalse(check({**VALID, 'component_type': 'WHOLE_BLOOD'}, three)[0])
        self.assertTrue(check({**VALID, 'component_type': 'WHOLE_BLOOD'})[0])


class QuantityTests(SimpleTestCase):
    def test_zero_and_negative_quantities_are_rejected(self):
        for bad in (0, -1, -10):
            with self.subTest(quantity=bad):
                ok, s = check({**VALID, 'quantity': bad})
                self.assertFalse(ok)
                self.assertEqual(s.errors['quantity'], ['Quantity must be at least 1 unit.'])

    def test_fractional_string_and_boolean_quantities_are_rejected(self):
        for bad in (1.5, 2.0, 0.1, '2', '1.5', '1e1', True, False, [2], {'units': 2}):
            with self.subTest(quantity=bad):
                ok, s = check({**VALID, 'quantity': bad})
                self.assertFalse(ok)
                self.assertEqual(s.errors['quantity'], ['Enter a whole number of units.'])

    def test_oversized_quantity_is_rejected_with_the_limit(self):
        for bad in (SYNTHETIC_POLICY.max_quantity + 1, 10 ** 12):
            with self.subTest(quantity=bad):
                ok, s = check({**VALID, 'quantity': bad})
                self.assertFalse(ok)
                self.assertEqual(s.errors['quantity'], ['Quantity cannot be more than 10 units.'])


class HostileFieldTests(SimpleTestCase):
    def test_client_cannot_supply_owner_status_or_server_fields(self):
        for name, value in [('requester_id', '00000000-0000-4000-8000-000000000001'),
                            ('requester', 'someone@example.test'), ('status', 'APPROVED'),
                            ('fulfilled_quantity', 2), ('id', '00000000-0000-4000-8000-000000000002'),
                            ('created_at', '2026-01-01T00:00:00Z'), ('rejection_reason', 'x'),
                            ('role', 'STAFF')]:
            with self.subTest(field=name):
                ok, s = check({**VALID, name: value})
                self.assertFalse(ok)
                self.assertEqual(s.errors, {'non_field_errors': ['Unexpected input field.']})
                messages = ' '.join(str(m) for m in s.errors['non_field_errors'])
                self.assertNotIn(name, messages)


class PolicyFailsClosedTests(SimpleTestCase):
    def test_missing_policy_raises_decision_required(self):
        with self.assertRaises(DecisionRequired):
            RequestCreateSerializer(data=VALID)
        with self.assertRaises(DecisionRequired):
            require_policy({'component_types': ('RBC',), 'max_quantity': 5})

    def test_malformed_policy_values_raise_decision_required(self):
        bad_policies = [
            dict(component_types=(), max_quantity=5),
            dict(component_types=['RBC'], max_quantity=5),
            dict(component_types=('RBC', 'RBC'), max_quantity=5),
            dict(component_types=('RBC', ''), max_quantity=5),
            dict(component_types=(' RBC',), max_quantity=5),
            dict(component_types=('RBC',), max_quantity=0),
            dict(component_types=('RBC',), max_quantity=True),
            dict(component_types=('RBC',), max_quantity=5.0),
            dict(component_types=('RBC',), max_quantity=None),
            dict(component_types=('CRYO',), max_quantity=5),  # not a database choice
            dict(component_types=('RBC',), max_quantity=101),  # above the database constraint
        ]
        for kwargs in bad_policies:
            with self.subTest(policy=kwargs):
                with self.assertRaises(DecisionRequired):
                    RequestInputPolicy(**kwargs)
