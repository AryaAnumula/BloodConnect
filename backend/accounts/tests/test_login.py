from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.services.login import LoginRejected, authenticate_user


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
    """MOCKED: establish_session (BB-02) and record_security_event (BB-05)
    are patched until those stories are merged. Replace with real integration later."""
    URL = '/api/v1/auth/login'
    PASSWORD = 'local-test-only-password'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='donor@example.test', password=self.PASSWORD)
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']
        p1 = patch('accounts.api.login.establish_session')
        p2 = patch('accounts.api.login.record_security_event')
        self.mock_session, self.mock_audit = p1.start(), p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def post(self, payload, token=True):
        extra = {'HTTP_X_CSRFTOKEN': self.token} if token else {}
        return self.client.post(self.URL, payload, content_type='application/json', **extra)

    def test_valid_login_200_matches_contract(self):
        r = self.post({'email': 'donor@example.test', 'password': self.PASSWORD})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['user']['email'], 'donor@example.test')
        self.assertEqual(body['user']['role'], 'DONOR')
        self.assertIn('session_expires_at', body)
        self.assertNotIn('password', r.content.decode())
        self.mock_session.assert_called_once()

    def test_wrong_password_and_unknown_email_give_same_401(self):
        a = self.post({'email': 'donor@example.test', 'password': 'wrong'})
        b = self.post({'email': 'nobody@example.test', 'password': 'wrong'})
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        ea, eb = a.json()['error'], b.json()['error']
        self.assertEqual(ea['code'], 'invalid_credentials')
        self.assertEqual((ea['code'], ea['message']), (eb['code'], eb['message']))
        self.assertEqual(set(ea), {'code', 'message', 'fields', 'request_id'})
        self.mock_session.assert_not_called()

    def test_inactive_user_401(self):
        self.user.is_active = False
        self.user.save()
        r = self.post({'email': 'donor@example.test', 'password': self.PASSWORD})
        self.assertEqual(r.status_code, 401)

    def test_missing_fields_400(self):
        r = self.post({'email': 'donor@example.test'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assertEqual(self.post({}).status_code, 400)

    def test_missing_csrf_token_403(self):
        r = self.post({'email': 'donor@example.test', 'password': self.PASSWORD}, token=False)
        self.assertEqual(r.status_code, 403)

    def test_protected_endpoint_blocks_anonymous(self):
        r = Client().get('/api/v1/auth/me')
        self.assertIn(r.status_code, (401, 403))