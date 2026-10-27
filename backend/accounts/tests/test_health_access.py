"""Component evidence: real audit writes, synthetic users, no endpoint integration."""
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import OperationalError
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.health_access import record_donor_health_denial
from accounts.permissions import may_view_donor_health
from audit.events import AuditUnavailable
from audit.models import SecurityEvent


def make_request(user):
    request = APIRequestFactory().get('/probe')
    request.user = user
    request.request_id = str(uuid4())
    return request


class DonorHealthDenialRecordingTests(TestCase):
    def test_authenticated_denial_records_one_event_with_actor_uuid_only(self):
        user = get_user_model().objects.create_user(
            email='other-donor@example.test', password='synthetic-only-password')
        request = make_request(user)
        record_donor_health_denial(request=request)
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.outcome), ('access_denied', 'denied'))
        self.assertEqual(event.actor_id, user.pk)
        self.assertEqual(str(event.request_id), request.request_id)

    def test_anonymous_denial_has_null_actor(self):
        record_donor_health_denial(request=make_request(AnonymousUser()))
        self.assertIsNone(SecurityEvent.objects.get().actor_id)

    def test_audit_failure_propagates_and_leaves_no_row(self):
        user = get_user_model().objects.create_user(
            email='audit-fail@example.test', password='synthetic-only-password')
        with patch('audit.events.SecurityEvent.objects.create',
                   side_effect=OperationalError('PRIVATE_DB_DETAIL')):
            with self.assertRaises(AuditUnavailable):
                record_donor_health_denial(request=make_request(user))
        self.assertFalse(SecurityEvent.objects.exists())

    def test_policy_helper_is_pure_and_writes_no_event(self):
        user = get_user_model().objects.create_user(
            email='pure@example.test', password='synthetic-only-password')
        self.assertFalse(may_view_donor_health(user=user, donor_user_id=uuid4()))
        self.assertFalse(SecurityEvent.objects.exists())