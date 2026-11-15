"""BB-17 requester predicate matrix (approved: active non-superuser REQUESTER only)."""
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase

from blood_requests.permissions import IsRequester, may_submit_request
from blood_requests.tests.helpers import make_clinical_staff, make_user


def fake(**kwargs):  # TEST-ONLY attribute bag; no database
    base = dict(is_authenticated=True, is_active=True, is_superuser=False, role='REQUESTER')
    return SimpleNamespace(**{**base, **kwargs})


class PredicateTests(SimpleTestCase):
    def test_only_active_non_superuser_requester_is_allowed(self):
        self.assertTrue(may_submit_request(user=fake()))
        for user in (None, AnonymousUser(), fake(is_authenticated=False), fake(is_active=False),
                     fake(is_superuser=True), fake(role='DONOR'), fake(role='STAFF'), fake(role='ADMIN'),
                     fake(role='requester'), fake(role=None), SimpleNamespace()):
            with self.subTest(user=vars(user) if user is not None else None):
                self.assertFalse(may_submit_request(user=user))

    def test_drf_class_uses_the_same_predicate(self):
        gate = IsRequester()
        self.assertTrue(gate.has_permission(SimpleNamespace(user=fake()), None))
        self.assertFalse(gate.has_permission(SimpleNamespace(user=fake(is_superuser=True)), None))


class RealAccountTests(TestCase):
    def test_clinical_permission_and_superuser_do_not_grant_submission(self):
        self.assertTrue(may_submit_request(user=make_user('REQUESTER')))
        self.assertFalse(may_submit_request(user=make_clinical_staff()))
        self.assertFalse(may_submit_request(user=make_user('REQUESTER', is_superuser=True, is_staff=True)))
