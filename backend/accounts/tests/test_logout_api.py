"""BB-02 logout API tests. Synthetic example.test users only."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone

URL = '/api/v1/auth/logout'
PASSWORD = 'local-test-only-password'


def session_key(client):
    return client.cookies[settings.SESSION_COOKIE_NAME].value


class LogoutApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='logout1@example.test', password=PASSWORD)

    def test_logout_returns_204_and_deletes_session(self):
        client = Client()
        client.force_login(self.user)
        key = session_key(client)
        self.assertTrue(Session.objects.filter(session_key=key).exists())
        response = client.post(URL)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_logout_clears_session_cookie(self):
        client = Client()
        client.force_login(self.user)
        response = client.post(URL)
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(cookie['max-age'], 0)
        self.assertEqual(cookie.value, '')

    def test_old_session_cookie_is_rejected_after_logout(self):
        client = Client()
        client.force_login(self.user)
        key = session_key(client)
        client.post(URL)
        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = key
        response = replay.post(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_second_logout_is_rejected(self):
        client = Client()
        client.force_login(self.user)
        client.post(URL)
        response = client.post(URL)
        self.assertEqual(response.status_code, 403)

    def test_missing_authentication_is_rejected(self):
        response = Client().post(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_invalid_session_cookie_is_rejected(self):
        client = Client()
        client.cookies[settings.SESSION_COOKIE_NAME] = 'not-a-real-session-key'
        response = client.post(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_expired_session_cookie_is_rejected(self):
        client = Client()
        client.force_login(self.user)
        key = session_key(client)
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(seconds=1))
        response = client.post(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'authentication_required')


class LogoutCsrfTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='csrf1@example.test', password=PASSWORD)

    def test_missing_csrf_token_is_rejected_and_session_survives(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        key = session_key(client)
        response = client.post(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'csrf_failed')
        self.assertTrue(Session.objects.filter(session_key=key).exists())

    def test_valid_csrf_token_allows_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        key = session_key(client)
        token = 'a' * 32  # synthetic token; cookie and header just have to match
        client.cookies[settings.CSRF_COOKIE_NAME] = token
        response = client.post(URL, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Session.objects.filter(session_key=key).exists())