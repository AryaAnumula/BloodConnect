"""Synthetic fixtures only. Real writes; failure injection is explicitly mocked."""
from uuid import uuid4
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError, OperationalError, transaction
from django.test import TestCase
from django.utils import timezone
from audit.events import AuditUnavailable, record_security_event
from audit.models import SecurityEvent


class EventWriterTests(TestCase):
    def record(self, **overrides):
        values = dict(event_type='login', actor_id=None, request_id=str(uuid4()), outcome='failure')
        values.update(overrides)
        return record_security_event(**values)

    def test_exact_pr30_failure_call_persists_once(self):
        before = timezone.now()
        self.assertIsNone(self.record())
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.outcome), ('login', 'failure'))
        self.assertIsNone(event.actor_id)
        self.assertGreaterEqual(event.occurred_at, before)
        self.assertTrue(timezone.is_aware(event.occurred_at))

    def test_exact_pr30_success_call_with_actor(self):
        actor = uuid4()
        self.record(actor_id=actor, outcome='success')
        event = SecurityEvent.objects.get()
        self.assertEqual((event.actor_id, event.outcome), (actor, 'success'))

    def test_access_denial_retains_actor_and_correlation(self):
        actor, correlation = uuid4(), uuid4()
        self.record(event_type='access_denied', outcome='denied', actor_id=actor, request_id=str(correlation))
        event = SecurityEvent.objects.get()
        self.assertEqual((event.actor_id, event.request_id), (actor, correlation))

    def test_unknown_or_mismatched_values_rejected(self):
        for values in [{'event_type': 'FREE_TEXT'}, {'outcome': 'FREE_TEXT'},
                       {'event_type': 'login', 'outcome': 'denied'},
                       {'event_type': 'access_denied', 'outcome': 'success'},
                       {'event_type': []}, {'outcome': {}}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.record(**values)
        self.assertEqual(SecurityEvent.objects.count(), 0)

    def test_invalid_identifiers_and_missing_success_actor_rejected(self):
        for values in [{'request_id': 'unsafe\r\nheader'}, {'request_id': ''},
                       {'request_id': None}, {'actor_id': 'not-uuid'}, {'outcome': 'success'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.record(**values)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_sensitive_keyword_arguments_not_supported(self):
        for field in ['password', 'token', 'health_data', 'payload', 'email', 'request']:
            with self.subTest(field=field), self.assertRaises(TypeError):
                self.record(**{field: 'SYNTHETIC_SECRET_DO_NOT_LOG'})
        self.assertFalse(SecurityEvent.objects.exists())

    def test_model_has_only_allowlisted_columns(self):
        self.assertEqual({f.name for f in SecurityEvent._meta.fields},
                         {'id', 'occurred_at', 'event_type', 'actor_id', 'request_id', 'outcome'})
        self.record()
        self.assertNotIn('SYNTHETIC_SECRET', str(SecurityEvent.objects.get()))

    def test_database_constraint_rejects_direct_invalid_pair(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SecurityEvent.objects.create(event_type='login', outcome='denied', request_id=uuid4())

    def test_database_constraint_rejects_success_without_actor(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SecurityEvent.objects.create(event_type='login', outcome='success', request_id=uuid4())

    def test_database_failure_becomes_redacted_exception_not_success(self):
        with patch('audit.events.SecurityEvent.objects.create', side_effect=OperationalError('PRIVATE_DB_DETAIL')):
            with self.assertRaises(AuditUnavailable) as result:
                self.record()
        self.assertNotIn('PRIVATE_DB_DETAIL', str(result.exception))
        self.assertFalse(SecurityEvent.objects.exists())
        self.record()  # Savepoint cleanup leaves the connection usable.
        self.assertEqual(SecurityEvent.objects.count(), 1)

    def test_events_survive_account_deletion_without_cascading(self):
        user = get_user_model().objects.create_user(email='audit-only@example.test', password='synthetic-only-password')
        actor = user.pk
        self.record(actor_id=actor)
        user.delete()
        self.assertEqual(SecurityEvent.objects.get().actor_id, actor)

    def test_outer_rollback_rolls_back_event_documented_limitation(self):
        with transaction.atomic():
            self.record()
            transaction.set_rollback(True)
        self.assertFalse(SecurityEvent.objects.exists())
