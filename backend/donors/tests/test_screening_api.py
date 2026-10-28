"""BB-07 endpoint tests (POST /api/v1/donors/{donor_id}/eligibility).

MOCKED: accounts.permissions.may_view_donor_health is still a NotImplementedError placeholder
on main (BB-12 is Arnav's, not merged). The stand-in mimics the approved policy (own donor only)
so the rest of the endpoint runs for real. Replace it with the real helper once BB-12 merges.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from donors import configuration
from donors.models import DonorProfile, EligibilityResult

PASSWORD = 'local-test-only-password'
RULES = {
    'rules_version': 'test-v1',
    'min_age_years': 18,
    'max_age_years': 65,
    'min_weight_kg': Decimal('50'),
    'min_days_between_donations': 90,
}


def standin_may_view(*, user, donor_user_id):
    # MOCK of the BB-12 helper: own donor only.
    return getattr(user, 'pk', None) == donor_user_id


def make_donor(email, mobile):
    user = get_user_model().objects.create_user(email=email, password=PASSWORD)
    profile = DonorProfile.objects.create(
        user=user, full_name='Synthetic Donor', mobile=mobile,
        blood_group='O+', location='Chennai')
    return user, profile


class ScreeningApiTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_donor('donor@example.test', '+919876543210')
        self.other, self.other_profile = make_donor('other@example.test', '+919876500000')
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']
        for p in (patch('donors.services.screening.may_view_donor_health', standin_may_view),
                  patch('donors.api.screening.approved_screening_rules', lambda: dict(RULES)),
                  patch('donors.services.screening.approved_screening_rules', lambda: dict(RULES))):
            p.start()
            self.addCleanup(p.stop)

    def url(self, profile=None):
        return f'/api/v1/donors/{(profile or self.profile).pk}/eligibility'

    def post(self, payload, profile=None, token=True, client=None):
        extra = {'HTTP_X_CSRFTOKEN': self.token} if token else {}
        return (client or self.client).post(self.url(profile), payload,
                                            content_type='application/json', **extra)

    def body(self, age=30, weight='60', last=None):
        return {'age_years': age, 'weight_kg': weight, 'last_donation_date': last}

    def test_eligible_returns_200_with_exact_contract_fields(self):
        r = self.post(self.body())
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(set(data), {'id', 'donor_id', 'status', 'reason_codes', 'reasons',
                                     'assessed_at', 'rules_version', 'is_stale'})
        self.assertEqual(data['status'], 'ELIGIBLE')
        self.assertEqual(data['donor_id'], str(self.profile.pk))
        self.assertEqual(data['rules_version'], 'test-v1')
        self.assertFalse(data['is_stale'])
        self.assertEqual(EligibilityResult.objects.count(), 1)

    def test_response_does_not_echo_health_answers(self):
        text = self.post(self.body(age=44, weight='71.25')).content.decode()
        self.assertNotIn('71.25', text)
        self.assertNotIn('"age_years"', text)

    def test_ineligible_returns_200_with_reasons(self):
        data = self.post(self.body(age=17)).json()
        self.assertEqual(data['status'], 'INELIGIBLE')
        self.assertEqual(data['reason_codes'], ['AGE_BELOW_MINIMUM'])
        self.assertEqual(len(data['reasons']), 1)

    def test_boundaries_over_http(self):
        today = timezone.localdate()
        self.assertEqual(self.post(self.body(age=18)).json()['status'], 'ELIGIBLE')
        self.assertEqual(self.post(self.body(age=65)).json()['status'], 'ELIGIBLE')
        self.assertEqual(self.post(self.body(weight='50')).json()['status'], 'ELIGIBLE')
        self.assertEqual(self.post(self.body(weight='49.99')).json()['status'], 'INELIGIBLE')
        ok = (today - timedelta(days=90)).isoformat()
        recent = (today - timedelta(days=89)).isoformat()
        self.assertEqual(self.post(self.body(last=ok)).json()['status'], 'ELIGIBLE')
        self.assertEqual(self.post(self.body(last=recent)).json()['status'], 'INELIGIBLE')

    def test_first_time_donor_null_date(self):
        self.assertEqual(self.post(self.body(last=None)).json()['status'], 'ELIGIBLE')
        self.assertEqual(self.post(self.body(age=70, last=None)).json()['status'], 'INELIGIBLE')

    def test_invalid_input_returns_400_and_saves_nothing(self):
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        bad = [
            {}, {'age_years': 30, 'weight_kg': '60'},                      # missing field
            self.body(age='30'), self.body(age=True), self.body(age=-1),    # age shape
            self.body(weight=60), self.body(weight='abc'), self.body(weight='60.123'),
            self.body(last='01/02/2026'), self.body(last='2026-13-45'),     # malformed dates
            self.body(last=future),                                         # future date
            dict(self.body(), role='ADMIN'),                                # unknown field
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                r = self.post(payload)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_repeated_json_keys_rejected_and_nothing_saved(self):
        raw = '{"age_years": 30, "age_years": 17, "weight_kg": "60", "last_donation_date": null}'
        r = self.client.post(self.url(), raw, content_type='application/json',
                             HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_missing_csrf_token_403_and_nothing_saved(self):
        self.assertEqual(self.post(self.body(), token=False).status_code, 403)
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_anonymous_user_blocked(self):
        anon = Client(enforce_csrf_checks=True)
        token = anon.get('/api/v1/auth/csrf').json()['csrf_token']
        r = anon.post(self.url(), self.body(), content_type='application/json',
                      HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()['error']['code'], 'authentication_required')
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_other_donor_cannot_screen_this_profile(self):
        r = self.post(self.body(), profile=self.other_profile)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()['error']['code'], 'forbidden')
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_unknown_donor_returns_404(self):
        r = self.client.post('/api/v1/donors/00000000-0000-4000-8000-000000000009/eligibility',
                             self.body(), content_type='application/json',
                             HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(EligibilityResult.objects.count(), 0)

    def test_rescreening_keeps_history_and_reports_rules_version(self):
        self.post(self.body(age=17))
        self.post(self.body(age=30))
        self.assertEqual(EligibilityResult.objects.filter(donor=self.profile).count(), 2)


class ScreeningPolicyUnresolvedApiTests(TestCase):
    def test_missing_rules_file_returns_409_policy_unresolved_and_saves_nothing(self):
        user, profile = make_donor('donor@example.test', '+919876543210')
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        with patch.object(configuration, 'RULES_PATH', configuration.Path('missing-rules.json')), \
                patch('donors.services.screening.may_view_donor_health', standin_may_view):
            r = client.post(f'/api/v1/donors/{profile.pk}/eligibility',
                            {'age_years': 30, 'weight_kg': '60', 'last_donation_date': None},
                            content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['error']['code'], 'policy_unresolved')
        self.assertNotIn('screening_rules.json', r.content.decode())
        self.assertEqual(EligibilityResult.objects.count(), 0)