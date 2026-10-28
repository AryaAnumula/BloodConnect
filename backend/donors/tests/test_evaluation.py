from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from donors.services.evaluation import evaluate

RULES = {
    'rules_version': 'test-version',
    'min_age_years': 18,
    'max_age_years': 65,
    'min_weight_kg': Decimal('50'),
    'min_days_between_donations': 90,
}
TODAY = date(2026, 10, 28)


def run(age=30, weight='60', last=None):
    return evaluate(age_years=age, weight_kg=Decimal(weight), last_donation_date=last,
                    today=TODAY, rules=RULES)


class EvaluationBoundaryTests(SimpleTestCase):
    def test_all_checks_pass_is_eligible(self):
        status, codes, reasons = run(last=TODAY - timedelta(days=200))
        self.assertEqual((status, codes, reasons), ('ELIGIBLE', [], []))

    def test_age_boundaries_are_inclusive(self):
        self.assertEqual(run(age=17)[1], ['AGE_BELOW_MINIMUM'])
        self.assertEqual(run(age=18)[0], 'ELIGIBLE')
        self.assertEqual(run(age=65)[0], 'ELIGIBLE')
        self.assertEqual(run(age=66)[1], ['AGE_ABOVE_MAXIMUM'])

    def test_weight_boundary_exactly_50_passes(self):
        self.assertEqual(run(weight='49.99')[1], ['WEIGHT_BELOW_MINIMUM'])
        self.assertEqual(run(weight='50')[0], 'ELIGIBLE')
        self.assertEqual(run(weight='50.00')[0], 'ELIGIBLE')
        self.assertEqual(run(weight='50.01')[0], 'ELIGIBLE')

    def test_donation_gap_boundary_exactly_90_days_passes(self):
        self.assertEqual(run(last=TODAY - timedelta(days=89))[1], ['DONATION_TOO_RECENT'])
        self.assertEqual(run(last=TODAY - timedelta(days=90))[0], 'ELIGIBLE')
        self.assertEqual(run(last=TODAY - timedelta(days=91))[0], 'ELIGIBLE')

    def test_donation_today_is_too_recent(self):
        self.assertEqual(run(last=TODAY)[1], ['DONATION_TOO_RECENT'])

    def test_first_time_donor_skips_only_the_gap_check(self):
        self.assertEqual(run(last=None)[0], 'ELIGIBLE')
        # Age and weight still apply to a first-time donor.
        self.assertEqual(run(age=17, last=None)[1], ['AGE_BELOW_MINIMUM'])
        self.assertEqual(run(weight='49', last=None)[1], ['WEIGHT_BELOW_MINIMUM'])
        self.assertEqual(run(age=70, weight='40', last=None)[0], 'INELIGIBLE')

    def test_multiple_failures_report_every_reason(self):
        status, codes, reasons = run(age=17, weight='49', last=TODAY - timedelta(days=10))
        self.assertEqual(status, 'INELIGIBLE')
        self.assertEqual(codes, ['AGE_BELOW_MINIMUM', 'WEIGHT_BELOW_MINIMUM',
                                 'DONATION_TOO_RECENT'])
        self.assertEqual(len(reasons), 3)

    def test_reason_messages_are_plain_text_without_inputs(self):
        _, _, reasons = run(age=17, weight='49.5')
        for message in reasons:
            self.assertNotIn('17', message)
            self.assertNotIn('49.5', message)