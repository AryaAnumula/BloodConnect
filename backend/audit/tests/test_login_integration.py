"""Runs against actual PR #30 login when present; skips on unchanged main stub.
No audit/authenticate mocks. Does NOT prove successful BB-02 session integration.
"""
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import Client, TestCase
from accounts.api import login as login_api
from audit.models import SecurityEvent


@skipUnless(hasattr(login_api, 'authenticate_user'), 'Actual BB-01 login is not integrated on this branch.')
class ActualLoginAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='audit-donor@example.test', password='synthetic-valid-password')
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/v1/auth/csrf').json()['csrf_token']

    def post(self, payload, csrf=True):
        return self.client.post('/api/v1/auth/login', payload, content_type='application/json',
                                **({'HTTP_X_CSRFTOKEN': self.csrf} if csrf else {}))

    def test_real_wrong_password_and_unknown_account_create_separate_failure_events(self):
        for email in [self.user.email, 'unknown@example.test']:
            response = self.post({'email': email, 'password': 'SYNTHETIC_SECRET_WRONG'})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error']['code'], 'invalid_credentials')
            self.assertNotIn('SYNTHETIC_SECRET', response.content.decode())
        self.assertEqual(SecurityEvent.objects.filter(event_type='login', outcome='failure', actor_id=None).count(), 2)

    def test_real_inactive_account_records_failure_without_actor_lookup_leak(self):
        self.user.is_active = False
        self.user.save()
        response = self.post({'email': self.user.email, 'password': 'synthetic-valid-password'})
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(SecurityEvent.objects.get().actor_id)

    def test_real_login_audit_storage_failure_is_redacted_503(self):
        with patch('audit.events.SecurityEvent.objects.create', side_effect=OperationalError('PRIVATE_DB_DETAIL')):
            response = self.post({'email': self.user.email, 'password': 'wrong'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'audit_unavailable')
        self.assertNotIn('PRIVATE_DB_DETAIL', response.content.decode())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_input_does_not_create_failed_credential_event(self):
        self.assertEqual(self.post({'email': self.user.email}).status_code, 400)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_csrf_rejection_precedes_credential_evaluation(self):
        self.assertEqual(self.post({'email': self.user.email, 'password': 'wrong'}, csrf=False).status_code, 403)
        self.assertFalse(SecurityEvent.objects.exists())
