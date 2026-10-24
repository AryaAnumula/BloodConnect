"""BB-02 tests. All users are synthetic example.test accounts."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.services.sessions import end_session, establish_session

PASSWORD = 'local-test-only-password'


def make_request():
    """Build a request that has a saved, anonymous session."""
    request = RequestFactory().post('/synthetic')
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    return request


class PasswordStorageTests(TestCase):
    def test_password_is_salted_hash_not_plaintext(self):
        user = get_user_model().objects.create_user(email='hash1@example.test', password=PASSWORD)
        self.assertNotIn(PASSWORD, user.password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password('wrong-password-value'))

    def test_same_password_gives_different_hashes(self):
        User = get_user_model()
        a = User.objects.create_user(email='salt1@example.test', password=PASSWORD)
        b = User.objects.create_user(email='salt2@example.test', password=PASSWORD)
        self.assertNotEqual(a.password, b.password)


class EstablishSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='sess1@example.test', password=PASSWORD)

    def test_login_stores_user_id_and_rotates_session_key(self):
        request = make_request()
        old_key = request.session.session_key
        establish_session(request=request, user=self.user)
        request.session.save()
        self.assertEqual(request.session[SESSION_KEY], str(self.user.pk))
        self.assertNotEqual(request.session.session_key, old_key)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())

    def test_session_does_not_store_password_or_hash(self):
        request = make_request()
        establish_session(request=request, user=self.user)
        request.session.save()
        stored = str(dict(request.session.items()))
        self.assertNotIn(PASSWORD, stored)
        self.assertNotIn(self.user.password, stored)

    def test_inactive_user_cannot_get_a_session(self):
        inactive = get_user_model().objects.create_user(
            email='inactive@example.test', password=PASSWORD, is_active=False)
        request = make_request()
        with self.assertRaises(ValueError):
            establish_session(request=request, user=inactive)
        self.assertNotIn(SESSION_KEY, request.session)


class EndSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='out1@example.test', password=PASSWORD)

    def test_logout_deletes_server_side_session(self):
        request = make_request()
        establish_session(request=request, user=self.user)
        request.session.save()
        key = request.session.session_key
        self.assertTrue(Session.objects.filter(session_key=key).exists())
        end_session(request=request)
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.assertNotIn(SESSION_KEY, request.session)

    def test_old_session_key_is_rejected_after_logout(self):
        request = make_request()
        establish_session(request=request, user=self.user)
        request.session.save()
        key = request.session.session_key
        end_session(request=request)
        self.assertNotIn(SESSION_KEY, SessionStore(session_key=key))

    def test_logout_without_login_does_not_crash(self):
        end_session(request=make_request())


class SessionExpiryTests(TestCase):
    def test_expired_session_is_rejected(self):
        user = get_user_model().objects.create_user(email='exp1@example.test', password=PASSWORD)
        request = make_request()
        establish_session(request=request, user=user)
        request.session.save()
        key = request.session.session_key
        self.assertIn(SESSION_KEY, SessionStore(session_key=key))
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(seconds=1))
        self.assertNotIn(SESSION_KEY, SessionStore(session_key=key))

    def test_provisional_policy_values_are_in_settings(self):
        # PROVISIONAL (D-04 not approved). Update deliberately if the team changes it.
        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)
        self.assertFalse(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')