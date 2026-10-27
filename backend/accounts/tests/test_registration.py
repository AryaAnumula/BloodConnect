from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from accounts.services.login import authenticate_user
from accounts.services.registration import register_donor
from donors.models import DonorProfile

PASSWORD = 'local-test-only-password'


def valid_payload(**overrides):
    data = {
        'email': 'new.donor@example.test',
        'mobile': '+919876543210',
        'password': PASSWORD,
        'full_name': 'Synthetic Donor',
        'blood_group': 'O+',
        'location': 'Chennai',
    }
    data.update(overrides)
    return data


class RegistrationApiTests(TestCase):
    URL = '/api/v1/auth/register'

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']

    def post(self, payload, token=True):
        extra = {'HTTP_X_CSRFTOKEN': self.token} if token else {}
        return self.client.post(self.URL, payload, content_type='application/json', **extra)

    def post_raw(self, raw_body):
        # Sends a raw JSON string so repeated keys are preserved exactly as written.
        return self.client.post(self.URL, raw_body, content_type='application/json',
                                HTTP_X_CSRFTOKEN=self.token)

    def assert_nothing_written(self):
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(DonorProfile.objects.count(), 0)

    def test_valid_registration_returns_201_matching_contract(self):
        r = self.post(valid_payload())
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(set(body), {'donor_id', 'user'})
        self.assertEqual(body['user']['email'], 'new.donor@example.test')
        self.assertEqual(body['user']['role'], 'DONOR')
        self.assertNotIn('password', r.content.decode())
        self.assertTrue(DonorProfile.objects.filter(id=body['donor_id']).exists())

    def test_password_is_hashed_not_stored_plain(self):
        self.post(valid_payload())
        user = get_user_model().objects.get(email='new.donor@example.test')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_missing_fields_400_with_field_errors(self):
        r = self.post({'email': 'new.donor@example.test'})
        self.assertEqual(r.status_code, 400)
        error = r.json()['error']
        self.assertEqual(error['code'], 'validation_error')
        for field in ('mobile', 'password', 'full_name', 'blood_group', 'location'):
            self.assertIn(field, error['fields'])

    def test_malformed_fields_400_and_nothing_created(self):
        for override in ({'email': 'not-an-email'}, {'mobile': '9876543210'},
                         {'mobile': '+12'}, {'password': 'short'},
                         {'blood_group': 'Z+'}, {'full_name': ''}, {'location': ''}):
            with self.subTest(override=override):
                self.assertEqual(self.post(valid_payload(**override)).status_code, 400)
        self.assert_nothing_written()

    def test_numeric_and_non_string_inputs_rejected_and_nothing_written(self):
        # Arya's finding: numbers were silently accepted as text.
        for override in ({'full_name': 12345}, {'location': 12345},
                         {'password': 123456789012}, {'email': 12345},
                         {'mobile': 919876543210}, {'full_name': True},
                         {'location': ['Chennai']}, {'password': None}):
            with self.subTest(override=override):
                r = self.post(valid_payload(**override))
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assert_nothing_written()

    def test_duplicate_json_keys_rejected_and_nothing_written(self):
        # Arya's finding: a repeated "email" key was accepted (last value won).
        raw = ('{"email": "first@example.test", "email": "second@example.test", '
               '"mobile": "+919876543210", "password": "local-test-only-password", '
               '"full_name": "Synthetic Donor", "blood_group": "O+", "location": "Chennai"}')
        r = self.post_raw(raw)
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('first@example.test', r.content.decode())
        self.assertNotIn('second@example.test', r.content.decode())
        self.assert_nothing_written()

    def test_duplicate_email_rejected_with_different_case(self):
        self.assertEqual(self.post(valid_payload()).status_code, 201)
        r = self.post(valid_payload(email='NEW.Donor@Example.Test', mobile='+919876500000'))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['error']['code'], 'duplicate_contact')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_duplicate_mobile_rejected(self):
        self.assertEqual(self.post(valid_payload()).status_code, 201)
        r = self.post(valid_payload(email='other.donor@example.test'))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['error']['code'], 'duplicate_contact')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_public_registration_rejects_privilege_fields(self):
        for extra in ({'role': 'ADMIN'}, {'is_staff': True}, {'is_superuser': True},
                      {'user_id': '00000000-0000-4000-8000-000000000002'}):
            with self.subTest(extra=extra):
                r = self.post(valid_payload(**extra))
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assert_nothing_written()

    def test_missing_csrf_token_403(self):
        self.assertEqual(self.post(valid_payload(), token=False).status_code, 403)
        self.assert_nothing_written()

    def test_registered_donor_can_sign_in_through_login_api(self):
        self.assertEqual(self.post(valid_payload()).status_code, 201)
        # Fresh client and CSRF token, as the browser would fetch after registering.
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        r = client.post('/api/v1/auth/login',
                        {'email': 'new.donor@example.test', 'password': PASSWORD},
                        content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['user']['role'], 'DONOR')


class RegisterDonorServiceTests(TestCase):
    def test_failed_profile_creation_leaves_no_partial_account(self):
        with patch('accounts.services.registration.DonorProfile.objects.create',
                   side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                register_donor(validated_data=valid_payload())
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(DonorProfile.objects.count(), 0)

    def test_unrelated_integrity_error_is_not_reported_as_duplicate(self):
        # Arya's finding: every IntegrityError was turned into duplicate_contact (409).
        # A failure with no conflicting email or mobile must surface as the real error.
        with patch('accounts.services.registration.DonorProfile.objects.create',
                   side_effect=IntegrityError('simulated non-contact constraint failure')):
            with self.assertRaises(IntegrityError):
                register_donor(validated_data=valid_payload())
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(DonorProfile.objects.count(), 0)

    def test_database_enforces_unique_mobile(self):
        register_donor(validated_data=valid_payload())
        other = get_user_model().objects.create_user(
            email='second@example.test', password=PASSWORD)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DonorProfile.objects.create(
                user=other, full_name='X', mobile='+919876543210',
                blood_group='A+', location='Y')

    def test_registered_donor_can_authenticate_at_service_level(self):
        register_donor(validated_data=valid_payload())
        user = authenticate_user(email='new.donor@example.test', password=PASSWORD)
        self.assertEqual(user.role, 'DONOR')