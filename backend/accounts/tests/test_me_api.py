"""BB-04 /auth/me tests. Synthetic example.test users only."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone

URL = '/api/v1/auth/me'
PASSWORD = 'local-test-only-password'


def make_user(role, name, **extra):
    return get_user_model().objects.create_user(
        email=f'{name}@example.test', password=PASSWORD, role=role, **extra)


class MeEndpointTests(TestCase):
    def test_each_role_gets_only_id_email_and_role(self):
        for role in get_user_model().Role.values:
            user = make_user(role, f'me-{role.lower()}')
            client = Client()
            client.force_login(user)
            response = client.get(URL)
            self.assertEqual(response.status_code, 200, role)
            self.assertEqual(
                response.json(),
                {'id': str(user.pk), 'email': user.email, 'role': role},
                role,
            )

    def test_response_never_contains_secrets_or_health_fields(self):
        user = make_user('DONOR', 'me-secret')
        client = Client()
        client.force_login(user)
        body = client.get(URL).json()
        self.assertEqual(set(body), {'id', 'email', 'role'})
        raw = str(body)
        self.assertNotIn('password', raw)
        self.assertNotIn(user.password, raw)

    def test_anonymous_is_rejected(self):
        response = Client().get(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_invalid_session_cookie_is_rejected(self):
        client = Client()
        client.cookies[settings.SESSION_COOKIE_NAME] = 'not-a-real-session-key'
        response = client.get(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_expired_session_is_rejected(self):
        client = Client()
        client.force_login(make_user('STAFF', 'me-expired'))
        key = client.cookies[settings.SESSION_COOKIE_NAME].value
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(seconds=1))
        response = client.get(URL)
        self.assertEqual(response.status_code, 403)

    def test_deactivated_account_session_is_rejected(self):
        user = make_user('DONOR', 'me-inactive')
        client = Client()
        client.force_login(user)
        get_user_model().objects.filter(pk=user.pk).update(is_active=False)
        response = client.get(URL)
        self.assertEqual(response.status_code, 403)
        