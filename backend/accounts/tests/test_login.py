from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import Client, TestCase

from accounts.services.login import LoginRejected, authenticate_user
from audit.models import SecurityEvent


class AuthenticateUserTests(TestCase):
    PASSWORD = 'local-test-only-password'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='donor@example.test', password=self.PASSWORD)

    def test_valid_credentials_return_user(self):
        user = authenticate_user(email='donor@example.test', password=self.PASSWORD)
        self.assertEqual(user.pk, self.user.pk)

    def test_email_is_case_and_whitespace_insensitive(self):
        user = authenticate_user(email='  DONOR@Example.Test ', password=self.PASSWORD)
        self.assertEqual(user.pk, self.user.pk)

    def test_wrong_password_rejected(self):
        with self.assertRaises(LoginRejected):
            authenticate_user(email='donor@example.test', password='wrong')

    def test_unknown_email_rejected(self):
        with self.assertRaises(LoginRejected):
            authenticate_user(email='nobody@example.test', password=self.PASSWORD)

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        with self.assertRaises(LoginRejected):
            authenticate_user(email='donor@example.test', password=self.PASSWORD)

    def test_blank_input_rejected(self):
        with self.assertRaises(LoginRejected):
            authenticate_user(email='', password='')


class LoginApiTests(TestCase):
    """Real BB-02 sessions and real BB-05 audit writer: nothing is mocked except
    deliberate failure injection in the tests that say so."""
    URL = '/api/v1/auth/login'
    PASSWORD = 'local-test-only-password'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='donor@example.test', password=self.PASSWORD)
        self.client = Client(enforce_csrf_checks=True, raise_request_exception=False)
        self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']

    def post(self, payload, token=True):
        extra = {'HTTP_X_CSRFTOKEN': self.token} if token else {}
        return self.client.post(self.URL, payload, content_type='application/json', **extra)

    def login(self):
        return self.post({'email': 'donor@example.test', 'password': self.PASSWORD})

    def test_valid_login_200_session_and_success_event(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['user']['email'], 'donor@example.test')
        self.assertEqual(body['user']['role'], 'DONOR')
        self.assertIn('session_expires_at', body)
        self.assertNotIn('password', r.content.decode())
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))
        event = SecurityEvent.objects.get(event_type='login', outcome='success')
        self.assertEqual(event.actor_id, self.user.pk)

    def test_wrong_password_and_unknown_email_give_same_401_and_failure_events(self):
        a = self.post({'email': 'donor@example.test', 'password': 'wrong'})
        b = self.post({'email': 'nobody@example.test', 'password': 'wrong'})
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        ea, eb = a.json()['error'], b.json()['error']
        self.assertEqual(ea['code'], 'invalid_credentials')
        self.assertEqual((ea['code'], ea['message']), (eb['code'], eb['message']))
        self.assertEqual(set(ea), {'code', 'message', 'fields', 'request_id'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(SecurityEvent.objects.filter(
            event_type='login', outcome='failure', actor_id=None).count(), 2)

    def test_inactive_user_401(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_missing_fields_400_and_no_event(self):
        r = self.post({'email': 'donor@example.test'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assertEqual(self.post({}).status_code, 400)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_missing_csrf_token_403(self):
        r = self.post({'email': 'donor@example.test', 'password': self.PASSWORD}, token=False)
        self.assertEqual(r.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_audit_failure_after_sign_in_leaves_no_usable_session(self):
        with patch('audit.events.SecurityEvent.objects.create',
                   side_effect=OperationalError('PRIVATE_DB_DETAIL')):
            r = self.login()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['error']['code'], 'audit_unavailable')
        self.assertNotIn('PRIVATE_DB_DETAIL', r.content.decode())
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 403)

    def test_session_failure_records_no_success_event(self):
        with patch('accounts.api.login.establish_session',
                   side_effect=RuntimeError('simulated session failure')):
            r = self.login()
        self.assertEqual(r.status_code, 500)
        self.assertFalse(SecurityEvent.objects.filter(outcome='success').exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_unlocks_authenticated_endpoint(self):
        # BB-04 (/me) is still a stub on main, so a signed-in user gets 501 instead of 200.
        # What this proves: anonymous is blocked (403) and the login session is accepted.
        self.assertEqual(Client().get('/api/v1/auth/me').status_code, 403)
        self.assertEqual(self.login().status_code, 200)
        self.assertNotEqual(self.client.get('/api/v1/auth/me').status_code, 403)