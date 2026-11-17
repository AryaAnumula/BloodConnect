from datetime import date, datetime, timedelta
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


def run(age=30, weight='60', last=None, confirmed=None):
    return evaluate(age_years=age, weight_kg=Decimal(weight), last_donation_date=last,
                    confirmed_collection_date=confirmed, today=TODAY, rules=RULES)


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

class ConfirmedDateTests(SimpleTestCase):
    """BC-D047: the evaluator itself takes the later of the two dates."""

    def test_confirmed_date_is_required_keyword(self):
        with self.assertRaises(TypeError):
            evaluate(age_years=30, weight_kg=Decimal('60'), last_donation_date=None,
                     today=TODAY, rules=RULES)

    def test_neither_date_skips_only_the_gap_check(self):
        self.assertEqual(run()[0], 'ELIGIBLE')
        self.assertEqual(run(age=17)[1], ['AGE_BELOW_MINIMUM'])

    def test_only_confirmed_date_applies_the_gap(self):
        self.assertEqual(run(confirmed=TODAY - timedelta(days=89))[1], ['DONATION_TOO_RECENT'])
        self.assertEqual(run(confirmed=TODAY - timedelta(days=90))[0], 'ELIGIBLE')

    def test_later_of_the_two_dates_wins_in_either_order(self):
        old, recent = TODAY - timedelta(days=200), TODAY - timedelta(days=10)
        self.assertEqual(run(last=old, confirmed=recent)[1], ['DONATION_TOO_RECENT'])
        self.assertEqual(run(last=recent, confirmed=old)[1], ['DONATION_TOO_RECENT'])
        self.assertEqual(run(last=old, confirmed=old)[0], 'ELIGIBLE')

    def test_gap_equality_with_the_confirmed_date_is_eligible(self):
        self.assertEqual(run(last=TODAY - timedelta(days=200),
                             confirmed=TODAY - timedelta(days=90))[0], 'ELIGIBLE')

    def test_invalid_or_future_dates_raise_value_error(self):
        future = TODAY + timedelta(days=1)
        for kwargs in ({'last': future}, {'confirmed': future},
                       {'confirmed': '2026-01-01'}, {'last': 20260101},
                       {'confirmed': datetime(2026, 1, 1)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run(**kwargs)
        with self.assertRaises(ValueError):
            evaluate(age_years=30, weight_kg=Decimal('60'), last_donation_date=None,
                     confirmed_collection_date=None, today='2026-10-28', rules=RULES)
