"""BB-17 runtime policy file: approved values load exactly; anything else fails closed."""
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from blood_requests.configuration import POLICY_PATH, approved_request_policy, load_request_policy
from core.errors import DecisionRequired

APPROVED = json.loads(POLICY_PATH.read_text(encoding='utf-8'))


class ApprovedPolicyTests(SimpleTestCase):
    def test_repository_policy_holds_the_approved_values(self):
        policy = approved_request_policy()
        self.assertEqual(policy.component_types, ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'))
        self.assertEqual(policy.max_quantity, 100)
        self.assertEqual(APPROVED['min_quantity'], 1)
        self.assertIs(APPROVED['demo_only'], True)
        self.assertIs(APPROVED['requires_current_stock'], False)
        self.assertEqual(APPROVED['policy_version'], 'bb17-college-demo-v1')


class FailClosedTests(SimpleTestCase):
    def load_text(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'policy.json'
            path.write_text(text, encoding='utf-8')
            return load_request_policy(path)

    def assert_fails(self, text):
        with self.assertRaises(DecisionRequired):
            self.load_text(text)

    def test_missing_file_fails(self):
        with self.assertRaises(DecisionRequired):
            load_request_policy('/definitely/missing/request-policy.json')

    def test_unreadable_or_non_object_json_fails(self):
        for text in ('', '{', '[]', '"x"', 'null'):
            with self.subTest(text=text):
                self.assert_fails(text)

    def test_missing_or_extra_keys_fail(self):
        for key in APPROVED:
            with self.subTest(missing=key):
                self.assert_fails(json.dumps({k: v for k, v in APPROVED.items() if k != key}))
        self.assert_fails(json.dumps({**APPROVED, 'default_quantity': 1}))

    def test_invalid_values_fail(self):
        bad_values = [
            ('max_quantity', 101), ('max_quantity', 0), ('max_quantity', True), ('max_quantity', '100'),
            ('max_quantity', None), ('min_quantity', 0), ('min_quantity', 2), ('min_quantity', True),
            ('component_types', []), ('component_types', ['RBC', 'RBC']), ('component_types', ['CRYO']),
            ('component_types', ['rbc']), ('component_types', 'RBC'), ('component_types', [1]),
            ('demo_only', False), ('demo_only', 'true'), ('requires_current_stock', True),
            ('requires_current_stock', None), ('policy_version', ''), ('policy_version', ' v1'),
            ('policy_version', 7),
        ]
        for key, value in bad_values:
            with self.subTest(key=key, value=value):
                self.assert_fails(json.dumps({**APPROVED, key: value}))

    def test_non_integer_and_non_finite_numbers_fail(self):
        for raw in ('100.0', '1e2', 'NaN', 'Infinity'):
            with self.subTest(raw=raw):
                self.assert_fails(json.dumps(APPROVED).replace('"max_quantity": 100', f'"max_quantity": {raw}'))

    def test_valid_narrower_policy_loads(self):
        policy = self.load_text(json.dumps({**APPROVED, 'component_types': ['RBC'], 'max_quantity': 5}))
        self.assertEqual((policy.component_types, policy.max_quantity), (('RBC',), 5))
