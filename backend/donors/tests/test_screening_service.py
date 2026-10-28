"""BB-07 service tests.

MOCKED: accounts.permissions.may_view_donor_health is still a NotImplementedError placeholder on
main (BB-12 is Arnav's, not merged). The stand-in below mimics the approved policy only so the
rest of screen_donor can run for real. Replace it with the real helper once BB-12 is merged.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from core.errors import DecisionRequired
from donors import configuration
from donors.models import DonorProfile, EligibilityResult
from donors.services import screening
from donors.services.screening import is_stale, screen_donor

PASSWORD = 'local-test-only-password'
RULES = {
    'rules_version': 'test-v1',
    'min_age_years': 18,
    'max_age_years': 65,
    'min_weight_kg': Decimal('50'),
    'min_days_between_donations': 90,
}


def standin_may_view(*, user, donor_user_id):
    # MOCK of the BB-12 helper: own donor only (staff access is not exercised here).
    return getattr(user, 'pk', None) == donor_user_id


def make_donor(email='donor@example.test', mobile='+919876543210'):
    user = get_user_model().objects.create_user(email=email, password=PASSWORD)
    profile = DonorProfile.objects.create(
        user=user, full_name='Synthetic Donor', mobile=mobile,
        blood_group='O+', location='Chennai')
    return user, profile


def answers(age=30, weight='60', last=None):
    return {'age_years': age, 'weight_kg': weight, 'last_donation_date': last}


class ScreenDonorTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_donor()
        patches = [
            patch('donors.services.screening.may_view_donor_health', standin_may_view),
            patch('donors.services.screening.approved_screening_rules',
                  lambda: dict(RULES)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def screen(self, **kwargs):
        return screen_donor(actor=self.user, donor_id=self.profile.pk, answers=answers(**kwargs))

    def test_eligible_result_is_saved_with_version_and_timestamp(self):
        result = self.screen()
        self.assertEqual(result.status, 'ELIGIBLE')
        self.assertEqual(result.reason_codes, [])
        self.assertEqual(result.rules_version, 'test-v1')
        self.assertIsNotNone(result.assessed_at)
        self.assertEqual(result.donor_id, self.profile.pk)
        self.assertEqual(EligibilityResult.objects.count(), 1)

    def test_ineligible_result_is_saved_with_reasons(self):
        result = self.screen(age=17, weight='49')
        self.assertEqual(result.status, 'INELIGIBLE')
        self.assertEqual(result.reason_codes, ['AGE_BELOW_MINIMUM', 'WEIGHT_BELOW_MINIMUM'])
        self.assertEqual(len(result.reasons), 2)
        self.assertEqual(EligibilityResult.objects.count(), 1)

    def test_boundary_values_through_the_service(self):
        today = timezone.localdate()
        self.assertEqual(self.screen(age=18)[0 if False else 'status'] if False else
                         self.screen(age=18).status, 'ELIGIBLE')
        self.assertEqual(self.screen(age=65).status, 'ELIGIBLE')
        self.assertEqual(self.screen(weight='50').status, 'ELIGIBLE')
        self.assertEqual(self.screen(last=today - timedelta(days=90)).status, 'ELIGIBLE')
        self.assertEqual(self.screen(last=today - timedelta(days=89)).status, 'INELIGIBLE')
        self.assertEqual(self.screen(age=66).status, 'INELIGIBLE')

    def test_first_time_donor_not_automatically_eligible(self):
        self.assertEqual(self.screen(last=None).status, 'ELIGIBLE')
        self.assertEqual(self.screen(age=17, last=None).status, 'INELIGIBLE')

    def test_rescreening_keeps_earlier_results_and_latest_is_newest(self):
        first = self.screen(age=17)
        second = self.screen(age=30)
        self.assertEqual(EligibilityResult.objects.filter(donor=self.profile).count(), 2)
        self.assertTrue(EligibilityResult.objects.filter(pk=first.pk).exists())
        latest = EligibilityResult.objects.filter(donor=self.profile).first()  # ordering -assessed_at
        self.assertEqual(latest.pk, second.pk)

    def test_invalid_input_rejected_and_nothing_saved(self):
        today = timezone.localdate()
        bad = [
            answers(age=-1), answers(age=True), answers(age='30'), answers(age=30.5),
            answers(weight=60), answers(weight='abc'), answers(weight='-5'), answers(weight='0'),
            answers(weight='NaN'), answers(weight='Infinity'),
            answers(last='2026-01-01'),                 # string, not a parsed date
            answers(last=today + timedelta(days=1)),    # future date
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    screen_donor(actor=self.user, donor_id=self.profile.pk, answers=payload)
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_non_dict_answers_rejected(self):
        with self.assertRaises(ValidationError):
            screen_donor(actor=self.user, donor_id=self.profile.pk, answers=['x'])
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_unknown_donor_is_not_found(self):
        with self.assertRaises(NotFound):
            screen_donor(actor=self.user, donor_id='00000000-0000-4000-8000-000000000009',
                         answers=answers())
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_another_donor_cannot_screen_this_profile(self):
        other, _ = make_donor(email='other@example.test', mobile='+919876500000')
        with self.assertRaises(PermissionDenied):
            screen_donor(actor=other, donor_id=self.profile.pk, answers=answers())
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_result_from_older_rules_version_is_stale(self):
        result = self.screen()
        self.assertFalse(is_stale(result, RULES))
        self.assertTrue(is_stale(result, dict(RULES, rules_version='test-v2')))


class ScreenDonorPolicyTests(TestCase):
    def test_missing_rules_file_requires_decision_and_saves_nothing(self):
        user, profile = make_donor()
        with patch.object(configuration, 'RULES_PATH', configuration.Path('missing-rules.json')):
            with patch('donors.services.screening.may_view_donor_health', standin_may_view):
                with self.assertRaises(DecisionRequired):
                    screen_donor(actor=user, donor_id=profile.pk, answers=answers())
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_deleting_the_account_deletes_profile_and_results(self):
        user, profile = make_donor()
        with patch('donors.services.screening.may_view_donor_health', standin_may_view), \
                patch('donors.services.screening.approved_screening_rules', lambda: dict(RULES)):
            screen_donor(actor=user, donor_id=profile.pk, answers=answers())
        user.delete()
        self.assertEqual(DonorProfile.objects.count(), 0)
        self.assertEqual(EligibilityResult.objects.count(), 0)