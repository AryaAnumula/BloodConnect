import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from core.errors import DecisionRequired
from donors import configuration
from donors.configuration import approved_screening_rules, load_rules

VALID = {
    'rules_version': 'test-version',
    'min_age_years': 18,
    'max_age_years': 65,
    'min_weight_kg': 50,
    'min_days_between_donations': 90,
}


class ScreeningConfigTests(SimpleTestCase):
    def write(self, content):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'rules.json'
        path.write_text(content if isinstance(content, str) else json.dumps(content),
                        encoding='utf-8')
        return path

    def variant(self, **changes):
        data = dict(VALID)
        data.update(changes)
        return self.write(data)

    def test_shipped_file_has_the_approved_demonstration_values(self):
        rules = approved_screening_rules()
        self.assertEqual(rules['min_age_years'], 18)
        self.assertEqual(rules['max_age_years'], 65)
        self.assertEqual(rules['min_weight_kg'], Decimal('50'))
        self.assertEqual(rules['min_days_between_donations'], 90)
        self.assertTrue(rules['rules_version'])

    def test_valid_file_loads(self):
        rules = load_rules(self.write(VALID))
        self.assertEqual(rules['rules_version'], 'test-version')
        self.assertEqual(rules['min_weight_kg'], Decimal('50'))

    def test_decimal_weight_loads(self):
        rules = load_rules(self.write(json.dumps(VALID).replace('"min_weight_kg": 50',
                                                                '"min_weight_kg": 49.5')))
        self.assertEqual(rules['min_weight_kg'], Decimal('49.5'))

    def test_missing_file_requires_decision(self):
        with self.assertRaises(DecisionRequired):
            load_rules(Path(tempfile.gettempdir()) / 'does-not-exist-rules.json')

    def test_approved_rules_use_decision_required_when_file_missing(self):
        with patch.object(configuration, 'RULES_PATH', Path('missing-rules.json')):
            with self.assertRaises(DecisionRequired):
                approved_screening_rules()

    def test_invalid_json_requires_decision(self):
        for content in ('', '{not json', '[]', 'null', '{"min_age_years": NaN}'):
            with self.subTest(content=content):
                with self.assertRaises(DecisionRequired):
                    load_rules(self.write(content))

    def test_missing_and_extra_keys_rejected(self):
        incomplete = dict(VALID)
        del incomplete['min_age_years']
        with self.assertRaises(DecisionRequired):
            load_rules(self.write(incomplete))
        with self.assertRaises(DecisionRequired):
            load_rules(self.variant(unexpected_rule=1))

    def test_wrong_types_rejected(self):
        for changes in ({'min_age_years': True}, {'max_age_years': 65.5},
                        {'min_age_years': '18'}, {'min_days_between_donations': 90.0},
                        {'min_weight_kg': '50'}, {'min_weight_kg': True},
                        {'rules_version': 1}, {'rules_version': ''},
                        {'rules_version': ' padded '}):
            with self.subTest(changes=changes):
                with self.assertRaises(DecisionRequired):
                    load_rules(self.variant(**changes))

    def test_out_of_range_values_rejected(self):
        for changes in ({'min_age_years': -1}, {'max_age_years': 17},
                        {'min_weight_kg': 0}, {'min_weight_kg': -5},
                        {'min_days_between_donations': -1}):
            with self.subTest(changes=changes):
                with self.assertRaises(DecisionRequired):
                    load_rules(self.variant(**changes))